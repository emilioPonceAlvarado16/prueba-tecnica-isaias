#!/bin/bash
set -e

# -----------------------------------------
# Despliegue del frontend (Next.js export estático) en S3 Website
# Lee API_URL / Cognito / bucket desde infra/.aws-outputs.env (generado por infra/aws.sh)
# -----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUTS="${SCRIPT_DIR}/infra/.aws-outputs.env"
# shellcheck disable=SC1090
[ -f "$OUTPUTS" ] && source "$OUTPUTS"

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
BUCKET_NAME="${BUCKET_NAME:-banco-andino-onboarding-${ACCOUNT_ID}}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"
FRONTEND_PROJECT_DIR="${FRONTEND_PROJECT_DIR:-${SCRIPT_DIR}/frontend}"
LOCAL_BUILD_DIR="${LOCAL_BUILD_DIR:-${FRONTEND_PROJECT_DIR}/out}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --------------------------------------
# Validaciones / Funciones auxiliares
# --------------------------------------
validate_aws_cli() {
  if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI no está instalado.${NC}"
    exit 1
  fi
}

configure_public_access() {
  aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration "$1" \
    --profile "$AWS_PROFILE"
}

# --------------------------------------
# 1. deploy_initial: bucket + website + policy pública de lectura
# --------------------------------------
deploy_initial() {
  echo -e "${YELLOW}Iniciando despliegue inicial (bucket ${BUCKET_NAME})...${NC}"

  if aws s3api head-bucket --bucket "$BUCKET_NAME" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo -e "${YELLOW}El bucket ya existe, se reconfigura.${NC}"
  elif [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" > /dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION" --profile "$AWS_PROFILE" > /dev/null
  fi

  configure_public_access "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false"

  aws s3 website "s3://$BUCKET_NAME" --index-document index.html --error-document 404.html --profile "$AWS_PROFILE"

  cat > "${SCRIPT_DIR}/bucket_policy.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    }
  ]
}
EOF
  aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "file://${SCRIPT_DIR}/bucket_policy.json" --profile "$AWS_PROFILE"
  aws s3api put-bucket-tagging --bucket "$BUCKET_NAME" --tagging 'TagSet=[{Key=project,Value=onb-demo}]' --profile "$AWS_PROFILE"

  echo -e "${GREEN}Bucket configurado exitosamente.${NC}"
}

# --------------------------------------
# 2. build_frontend: variables de producción
# --------------------------------------
build_frontend() {
  echo -e "${YELLOW}Construyendo frontend con variables de producción...${NC}"

  if [ -z "$API_URL" ]; then
    echo -e "${RED}ERROR: falta API_URL (ejecuta infra/aws.sh --create primero).${NC}"
    exit 1
  fi

  cd "$FRONTEND_PROJECT_DIR"

  cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=${API_URL}
NEXT_PUBLIC_COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
NEXT_PUBLIC_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
EOF
  echo -e "${YELLOW}Variables de producción:${NC}"
  cat .env.production

  [ -d "node_modules" ] || npm install

  # .env.local tiene prioridad sobre .env.production en Next.js: se fuerzan por entorno
  if ! NEXT_PUBLIC_API_URL="$API_URL" \
       NEXT_PUBLIC_COGNITO_USER_POOL_ID="$COGNITO_USER_POOL_ID" \
       NEXT_PUBLIC_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
       npm run build; then
    echo -e "${RED}ERROR: El build falló${NC}"
    cd - > /dev/null
    exit 1
  fi

  cd - > /dev/null
  echo -e "${GREEN}Frontend construido exitosamente.${NC}"
}

# --------------------------------------
# 3. deploy_update: build + sync
# --------------------------------------
deploy_update() {
  echo -e "${YELLOW}Iniciando actualización...${NC}"
  build_frontend

  aws s3 sync "$LOCAL_BUILD_DIR" "s3://$BUCKET_NAME" \
    --delete \
    --exclude "*.git/*" \
    --exclude ".DS_Store" \
    --profile "$AWS_PROFILE"

  echo -e "${GREEN}Contenido actualizado exitosamente.${NC}"
}

# --------------------------------------
# 4. destroy
# --------------------------------------
destroy() {
  echo -e "${RED}Iniciando destrucción de recursos...${NC}"
  aws s3 rm "s3://$BUCKET_NAME" --recursive --profile "$AWS_PROFILE" || true
  aws s3api delete-bucket --bucket "$BUCKET_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE"
  echo -e "${GREEN}Recursos eliminados satisfactoriamente.${NC}"
}

# --------------------------------------
# MAIN
# --------------------------------------
validate_aws_cli

case "$1" in
  --initial)
    deploy_initial
    deploy_update
    ;;
  --update)
    deploy_update
    ;;
  --destroy)
    destroy
    ;;
  *)
    echo -e "${RED}Uso:"
    echo -e "  $0 --initial  : Primer despliegue (bucket + website + build + sync)"
    echo -e "  $0 --update   : Re-build y sync del sitio"
    echo -e "  $0 --destroy  : Eliminar bucket S3${NC}"
    exit 1
    ;;
esac

rm -f "${SCRIPT_DIR}/bucket_policy.json" 2> /dev/null || true

echo -e "\n${GREEN}¡Operación completada!${NC}"
if [ "$1" = "--initial" ] || [ "$1" = "--update" ]; then
  echo -e "S3 Website URL:   ${YELLOW}http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com${NC}"
fi
