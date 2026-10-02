# Onboarding Digital Multi-Agente — Banco Andino Demo (PoC)

Orquestador **LangGraph** que coordina 4 agentes (identidad, listas de riesgo, políticas con RAG, respuesta) para decidir si un prospecto es apto, con escalamiento y soluciones propuestas cuando algo falla o es ambiguo.

**Stack:** Python 3.12 · Flask + flask-smorest + marshmallow · LangGraph · OpenAI (gpt-4.1-mini, text-embedding-3-small) · PostgreSQL 16 + pgvector · Next.js · AWS (S3, API Gateway, Lambda, Cognito, RDS).

```bash
./manage_env.sh setup        # local: BD + RAG + API (:8010) + frontend (:3000)
infra/aws.sh --create && ./deploy.sh --initial   # AWS
```

| Documento | Contenido |
|---|---|
| [docs/propuesta/PROPUESTA_TECNICA.md](docs/propuesta/PROPUESTA_TECNICA.md) | Propuesta aprobada, políticas, DDL, decisiones |
| [docs/arquitectura/ARQUITECTURA.md](docs/arquitectura/ARQUITECTURA.md) | Diagramas de despliegue y del grafo |
| [docs/rag/PIPELINE_RAG.md](docs/rag/PIPELINE_RAG.md) · [EVALUACION_RAG.md](docs/rag/EVALUACION_RAG.md) | Pipeline RAG y su evaluación |
| [docs/api/API.md](docs/api/API.md) | Endpoints y códigos de resultado |
| [docs/operacion/OPERACION.md](docs/operacion/OPERACION.md) | Scripts local / AWS |
| [docs/pruebas/PRUEBAS.md](docs/pruebas/PRUEBAS.md) · [RESULTADOS_PRUEBAS.md](docs/pruebas/RESULTADOS_PRUEBAS.md) | Usuarios de prueba y resultados |

```
backend/     app/{agents,graph,tools,rag,domain,contracts,services,api,provisioning} · tests · scripts
frontend/    Next.js (export estático)
db/          ddl/ · seeds/
policies/    src/ (fuente) · docs/ (PDF/MD/TXT ingeridos)
lambdas/     cognito_provisioner/
infra/       aws.sh
```
