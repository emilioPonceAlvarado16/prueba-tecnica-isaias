# Operación

## Local
```bash
cp .env.example .env            # OPENAI_API_KEY
./manage_env.sh setup           # BD (DDL+seeds) + RAG + API + frontend
./manage_env.sh start|stop|restart [all|db|api|frontend]
./manage_env.sh status | logs api
./manage_env.sh test            # pytest
./manage_env.sh scenarios --reset --write-doc
```

## AWS (us-east-1, perfil default)
```bash
infra/aws.sh --create           # SSM, RDS, Cognito, roles, Lambdas, API Gateway (idempotente)
./deploy.sh --initial           # bucket S3 website + build + sync  (luego: --update)
infra/aws.sh --api              # republicar solo la imagen de la API
infra/aws.sh --destroy && ./deploy.sh --destroy
```
Salidas (URLs, ids) en `infra/.aws-outputs.env`. Secretos en SSM `/onb-demo/*` (SecureString).

**Nota PoC:** RDS es público con 5432 abierto (Lambda fuera de VPC no tiene IP fija); SSL obligatorio y clave aleatoria de 32 caracteres. Para producción: Lambda en VPC + NAT o VPC endpoints.
Costo aproximado encendido: RDS db.t4g.micro ~US$13–15/mes; el resto es prácticamente gratis a este volumen.
