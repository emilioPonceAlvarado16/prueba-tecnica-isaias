#!/bin/bash
set -e

# -----------------------------------------
# Infraestructura AWS del onboarding (PoC)
#   RDS PostgreSQL 16 + pgvector · SSM · Cognito · Lambda provisioner · Lambda API (imagen) · API Gateway HTTP
# Uso:
#   infra/aws.sh --create     crea / actualiza todo (idempotente)
#   infra/aws.sh --db         solo inicializa la BD remota (DDL + seeds + ingesta RAG)
#   infra/aws.sh --api        reconstruye y publica solo la imagen de la API
#   infra/aws.sh --status     muestra salidas
#   infra/aws.sh --destroy    elimina todo
# -----------------------------------------
PROJECT="${PROJECT:-onb-demo}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"
export AWS_REGION AWS_PROFILE AWS_PAGER=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUTS="${SCRIPT_DIR}/.aws-outputs.env"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DB_ID="${PROJECT}-postgres"
DB_NAME="onboarding"
DB_USER="onboarding_admin"
SG_NAME="${PROJECT}-rds-sg"
ECR_REPO="${PROJECT}-api"
API_FN="${PROJECT}-api"
PROV_FN="${PROJECT}-cognito-provisioner"
API_ROLE="${PROJECT}-api-role"
PROV_ROLE="${PROJECT}-provisioner-role"
POOL_NAME="${PROJECT}-users"
BUCKET_NAME="${BUCKET_NAME:-banco-andino-onboarding-${ACCOUNT_ID}}"
FRONT_ORIGIN="http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "${YELLOW}▶ ${1}${NC}"; }
ok()   { echo -e "${GREEN}✓ ${1}${NC}"; }
fail() { echo -e "${RED}✗ ${1}${NC}"; exit 1; }

save_output() {
  touch "$OUTPUTS"
  grep -v "^${1}=" "$OUTPUTS" > "${OUTPUTS}.tmp" || true
  mv "${OUTPUTS}.tmp" "$OUTPUTS"
  echo "${1}=${2}" >> "$OUTPUTS"
}

ssm_get() { aws ssm get-parameter --name "/${PROJECT}/${1}" --with-decryption --query Parameter.Value --output text 2>/dev/null; }
ssm_put() { aws ssm put-parameter --name "/${PROJECT}/${1}" --value "$2" --type SecureString --overwrite > /dev/null; }

# --------------------------------------
# 1. Secretos (SSM Parameter Store)
# --------------------------------------
create_secrets() {
  step "Secretos en SSM (/${PROJECT}/*)"
  [ -f "${ROOT_DIR}/.env" ] || fail "Falta .env con OPENAI_API_KEY"
  local key
  key=$(grep '^OPENAI_API_KEY=' "${ROOT_DIR}/.env" | cut -d= -f2-)
  ssm_put "openai_api_key" "$key"
  if [ -z "$(ssm_get db_password)" ]; then
    ssm_put "db_password" "$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 32)"
  fi
  ok "openai_api_key y db_password guardados como SecureString"
}

# --------------------------------------
# 2. RDS PostgreSQL 16 (pgvector)
# --------------------------------------
create_rds() {
  step "RDS PostgreSQL (${DB_ID})"
  local vpc sg
  vpc=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
  sg=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$SG_NAME" Name=vpc-id,Values="$vpc" \
        --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)
  if [ "$sg" = "None" ] || [ -z "$sg" ]; then
    sg=$(aws ec2 create-security-group --group-name "$SG_NAME" --vpc-id "$vpc" \
          --description "PoC onboarding: PostgreSQL (SSL obligatorio)" --query GroupId --output text)
    # Lambda fuera de VPC no tiene IP fija: 5432 abierto con SSL forzado + clave de 32 chars (ver docs/operacion)
    aws ec2 authorize-security-group-ingress --group-id "$sg" --protocol tcp --port 5432 --cidr 0.0.0.0/0 > /dev/null
  fi
  save_output RDS_SG "$sg"

  if aws rds describe-db-instances --db-instance-identifier "$DB_ID" > /dev/null 2>&1; then
    ok "RDS ya existe"
  else
    aws rds create-db-instance \
      --db-instance-identifier "$DB_ID" \
      --engine postgres --engine-version 16.15 \
      --db-instance-class db.t4g.micro \
      --allocated-storage 20 --storage-type gp3 \
      --db-name "$DB_NAME" \
      --master-username "$DB_USER" \
      --master-user-password "$(ssm_get db_password)" \
      --vpc-security-group-ids "$sg" \
      --publicly-accessible \
      --backup-retention-period 0 \
      --no-multi-az \
      --tags Key=project,Value="$PROJECT" > /dev/null
    ok "RDS en creación (tarda ~5-10 min)"
  fi
}

wait_rds() {
  step "Esperando RDS disponible..."
  aws rds wait db-instance-available --db-instance-identifier "$DB_ID"
  local host url
  host=$(aws rds describe-db-instances --db-instance-identifier "$DB_ID" --query "DBInstances[0].Endpoint.Address" --output text)
  url="postgresql://${DB_USER}:$(ssm_get db_password)@${host}:5432/${DB_NAME}?sslmode=require"
  ssm_put "database_url" "$url"
  save_output RDS_HOST "$host"
  ok "RDS disponible: ${host}"
}

# --------------------------------------
# 3. Inicializar BD remota: DDL + seeds + ingesta RAG (desde esta máquina)
# --------------------------------------
init_db() {
  step "Inicializando BD remota (DDL + seeds + RAG)"
  local url
  url=$(ssm_get database_url)
  local psql_cmd=(docker run --rm -i pgvector/pgvector:pg16 psql "$url" -v ON_ERROR_STOP=1 -q)
  if [ "$("${psql_cmd[@]}" -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name='core'")" != "1" ]; then
    "${psql_cmd[@]}" < "${ROOT_DIR}/db/ddl/001_schema.sql"
    ok "DDL aplicado"
  fi
  for seed in "${ROOT_DIR}"/db/seeds/*.sql; do
    "${psql_cmd[@]}" < "$seed"
  done
  ok "Seeds aplicados"
  (cd "${ROOT_DIR}/backend" && DATABASE_URL="$url" uv run python -m app.rag.ingest)
  ok "Ingesta RAG completa"
}

# --------------------------------------
# 4. Cognito User Pool
# --------------------------------------
create_cognito() {
  step "Cognito User Pool (${POOL_NAME})"
  local pool client
  pool=$(aws cognito-idp list-user-pools --max-results 60 --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" --output text)
  if [ "$pool" = "None" ] || [ -z "$pool" ]; then
    pool=$(aws cognito-idp create-user-pool --pool-name "$POOL_NAME" \
      --policies 'PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=true,TemporaryPasswordValidityDays=7}' \
      --schema Name=product,AttributeDataType=String,Mutable=true Name=onboarding_id,AttributeDataType=String,Mutable=true \
      --admin-create-user-config AllowAdminCreateUserOnly=true \
      --user-pool-tags project="$PROJECT" \
      --query UserPool.Id --output text)
  fi
  client=$(aws cognito-idp list-user-pool-clients --user-pool-id "$pool" --query "UserPoolClients[?ClientName=='${PROJECT}-web'].ClientId | [0]" --output text)
  if [ "$client" = "None" ] || [ -z "$client" ]; then
    client=$(aws cognito-idp create-user-pool-client --user-pool-id "$pool" --client-name "${PROJECT}-web" \
      --no-generate-secret \
      --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
      --query UserPoolClient.ClientId --output text)
  fi
  save_output COGNITO_USER_POOL_ID "$pool"
  save_output COGNITO_CLIENT_ID "$client"
  ok "User Pool ${pool} · App client ${client}"
}

# --------------------------------------
# 5. Roles IAM (mínimo privilegio)
# --------------------------------------
ensure_role() {
  local role="$1" policy="$2"
  if ! aws iam get-role --role-name "$role" > /dev/null 2>&1; then
    aws iam create-role --role-name "$role" --assume-role-policy-document '{
      "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' > /dev/null
    aws iam attach-role-policy --role-name "$role" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  fi
  aws iam put-role-policy --role-name "$role" --policy-name "${role}-inline" --policy-document "$policy"
}

create_roles() {
  step "Roles IAM"
  # shellcheck disable=SC1090
  source "$OUTPUTS"
  ensure_role "$PROV_ROLE" "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",
    \"Action\":[\"cognito-idp:AdminCreateUser\",\"cognito-idp:AdminGetUser\"],
    \"Resource\":\"arn:aws:cognito-idp:${AWS_REGION}:${ACCOUNT_ID}:userpool/${COGNITO_USER_POOL_ID}\"}]}"
  ensure_role "$API_ROLE" "{\"Version\":\"2012-10-17\",\"Statement\":[
    {\"Effect\":\"Allow\",\"Action\":\"lambda:InvokeFunction\",\"Resource\":\"arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${PROV_FN}\"},
    {\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParametersByPath\",\"ssm:GetParameter\"],\"Resource\":\"arn:aws:ssm:${AWS_REGION}:${ACCOUNT_ID}:parameter/${PROJECT}*\"}]}"
  sleep 10   # propagación de IAM
  ok "Roles ${API_ROLE} y ${PROV_ROLE}"
}

# --------------------------------------
# 6. Lambda cognito-provisioner (zip)
# --------------------------------------
deploy_provisioner() {
  step "Lambda ${PROV_FN}"
  # shellcheck disable=SC1090
  source "$OUTPUTS"
  local zip="/tmp/${PROV_FN}.zip"
  (cd "${ROOT_DIR}/lambdas/cognito_provisioner" && rm -f "$zip" && zip -q "$zip" handler.py)
  local env="{\"Variables\":{\"USER_POOL_ID\":\"${COGNITO_USER_POOL_ID}\",\"DEMO_MODE\":\"true\"}}"
  if aws lambda get-function --function-name "$PROV_FN" > /dev/null 2>&1; then
    aws lambda update-function-code --function-name "$PROV_FN" --zip-file "fileb://${zip}" > /dev/null
    aws lambda wait function-updated --function-name "$PROV_FN"
    aws lambda update-function-configuration --function-name "$PROV_FN" --environment "$env" > /dev/null
  else
    aws lambda create-function --function-name "$PROV_FN" --runtime python3.12 --architectures arm64 \
      --handler handler.handler --zip-file "fileb://${zip}" --timeout 15 --memory-size 256 \
      --role "arn:aws:iam::${ACCOUNT_ID}:role/${PROV_ROLE}" --environment "$env" > /dev/null
  fi
  aws lambda wait function-active-v2 --function-name "$PROV_FN"
  aws lambda wait function-updated-v2 --function-name "$PROV_FN"
  ok "Provisioner desplegado"
}

# --------------------------------------
# 7. Lambda API (imagen contenedor en ECR)
# --------------------------------------
deploy_api() {
  step "Imagen de la API -> ECR"
  local registry="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  local image="${registry}/${ECR_REPO}:$(date +%Y%m%d%H%M%S)"
  aws ecr describe-repositories --repository-names "$ECR_REPO" > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name "$ECR_REPO" --image-scanning-configuration scanOnPush=true > /dev/null
  aws ecr get-login-password | docker login --username AWS --password-stdin "$registry" > /dev/null
  docker buildx build --platform linux/arm64 --provenance=false -f "${ROOT_DIR}/backend/Dockerfile.lambda" \
    -t "$image" --push "${ROOT_DIR}/backend"
  ok "Imagen publicada: ${image}"

  step "Lambda ${API_FN}"
  local env="{\"Variables\":{\"SSM_PREFIX\":\"/${PROJECT}\",\"PROVISIONER\":\"lambda\",\"PROVISIONER_LAMBDA_NAME\":\"${PROV_FN}\",\"DEMO_MODE\":\"true\",\"CORS_ORIGINS\":\"${FRONT_ORIGIN},http://localhost:3000\",\"CACHE_DIR\":\"/tmp/cache\",\"TIKTOKEN_CACHE_DIR\":\"/tmp/tiktoken\",\"OPENAI_CHAT_MODEL\":\"gpt-4.1-mini\"}}"
  if aws lambda get-function --function-name "$API_FN" > /dev/null 2>&1; then
    aws lambda update-function-code --function-name "$API_FN" --image-uri "$image" > /dev/null
    aws lambda wait function-updated --function-name "$API_FN"
    aws lambda update-function-configuration --function-name "$API_FN" --environment "$env" > /dev/null
  else
    aws lambda create-function --function-name "$API_FN" --package-type Image --code ImageUri="$image" \
      --architectures arm64 --timeout 60 --memory-size 1024 \
      --role "arn:aws:iam::${ACCOUNT_ID}:role/${API_ROLE}" --environment "$env" > /dev/null
  fi
  aws lambda wait function-active-v2 --function-name "$API_FN"
  aws lambda wait function-updated-v2 --function-name "$API_FN"
  ok "API Lambda desplegada"
}

# --------------------------------------
# 8. API Gateway HTTP API -> Lambda
# --------------------------------------
create_api_gateway() {
  step "API Gateway HTTP API"
  local api_id fn_arn
  fn_arn="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${API_FN}"
  api_id=$(aws apigatewayv2 get-apis --query "Items[?Name=='${PROJECT}-http'].ApiId | [0]" --output text)
  if [ "$api_id" = "None" ] || [ -z "$api_id" ]; then
    api_id=$(aws apigatewayv2 create-api --name "${PROJECT}-http" --protocol-type HTTP --target "$fn_arn" \
      --query ApiId --output text)
    aws lambda add-permission --function-name "$API_FN" --statement-id apigw-invoke --action lambda:InvokeFunction \
      --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${api_id}/*" > /dev/null
  fi
  save_output API_URL "https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com"
  save_output API_ID "$api_id"
  save_output FRONT_ORIGIN "$FRONT_ORIGIN"
  save_output BUCKET_NAME "$BUCKET_NAME"
  ok "API: https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com"
}

status() {
  [ -f "$OUTPUTS" ] && cat "$OUTPUTS" || echo "Sin salidas aún"
}

# --------------------------------------
# Destroy
# --------------------------------------
destroy() {
  echo -e "${RED}Eliminando recursos de ${PROJECT}...${NC}"
  # shellcheck disable=SC1090
  [ -f "$OUTPUTS" ] && source "$OUTPUTS"
  [ -n "$API_ID" ] && aws apigatewayv2 delete-api --api-id "$API_ID" || true
  aws lambda delete-function --function-name "$API_FN" 2>/dev/null || true
  aws lambda delete-function --function-name "$PROV_FN" 2>/dev/null || true
  aws ecr delete-repository --repository-name "$ECR_REPO" --force > /dev/null 2>&1 || true
  [ -n "$COGNITO_USER_POOL_ID" ] && aws cognito-idp delete-user-pool --user-pool-id "$COGNITO_USER_POOL_ID" || true
  for role in "$API_ROLE" "$PROV_ROLE"; do
    aws iam delete-role-policy --role-name "$role" --policy-name "${role}-inline" 2>/dev/null || true
    aws iam detach-role-policy --role-name "$role" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
    aws iam delete-role --role-name "$role" 2>/dev/null || true
  done
  aws rds delete-db-instance --db-instance-identifier "$DB_ID" --skip-final-snapshot > /dev/null 2>&1 || true
  echo -e "${YELLOW}RDS eliminándose; el security group ${SG_NAME} se borra cuando termine:${NC}"
  echo "  aws rds wait db-instance-deleted --db-instance-identifier ${DB_ID} && aws ec2 delete-security-group --group-id ${RDS_SG}"
  for p in openai_api_key db_password database_url; do
    aws ssm delete-parameter --name "/${PROJECT}/${p}" 2>/dev/null || true
  done
  rm -f "$OUTPUTS"
  ok "Recursos eliminados (frontend: ./deploy.sh --destroy)"
}

case "$1" in
  --create)
    create_secrets; create_rds; create_cognito; create_roles; deploy_provisioner
    wait_rds; init_db; deploy_api; create_api_gateway; status ;;
  --db)      init_db ;;
  --api)     deploy_api ;;
  --status)  status ;;
  --destroy) destroy ;;
  --step)    shift; for fn in "$@"; do "$fn"; done ;;
  *) echo "Uso: $0 --create | --db | --api | --status | --destroy"; exit 1 ;;
esac
