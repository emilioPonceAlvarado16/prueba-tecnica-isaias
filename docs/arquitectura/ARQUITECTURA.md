# Arquitectura

## Despliegue

```mermaid
flowchart LR
    U((Prospecto)) -->|HTTP| S3["S3 Website<br/>Next.js export"]
    S3 -->|fetch| APIGW["API Gateway HTTP"]
    APIGW --> L1["Lambda onb-demo-api<br/>Flask + LangGraph (imagen arm64)"]
    L1 --> RDS[("RDS PostgreSQL 16 + pgvector<br/>core · ext · rag · checkpoint")]
    L1 --> OAI[[OpenAI<br/>gpt-4.1-mini · text-embedding-3-small]]
    L1 -->|"APPROVED → invoke"| L2["Lambda onb-demo-cognito-provisioner"]
    L2 -->|AdminCreateUser| COG["Cognito User Pool"]
    L1 -.-> SSM["SSM Parameter Store"]
```
En local: Next.js `:3000` → Flask `:8010` → PostgreSQL Docker `:5433`; la provisión usa un mock (`core.provisioned_user`).

## Grafo del orquestador (LangGraph)

```mermaid
flowchart TD
    S([START]) --> V[validate_input<br/>cédula módulo 10]
    V -->|inválida| D
    V --> I[identity_agent<br/>verify_identity]
    I -->|falla / confianza<0.8 / nombre / edad| D
    I --> R[risk_agent<br/>check_risk_lists]
    R -->|high / tool caído| D
    R -->|medium PEP| H{{request_customer_info<br/>interrupt → AWAITING_CUSTOMER}}
    H -->|POST /continue| P
    R -->|low| P[policy_agent<br/>search_policies RAG + prepare_documentation]
    P --> D[decision<br/>reglas determinísticas]
    D -->|APPROVED| PR[provision_user<br/>mock local / Lambda→Cognito]
    D -->|otro| RS
    PR --> RS[response_agent<br/>LLM + guardrails POL-COM-005]
    RS --> F[finalize<br/>persistencia + escalamiento] --> E([END])
```

## Principios
| Tema | Implementación |
|---|---|
| Control de tools | `ToolGate`: RAG de tools (`rag.tool_embedding`) ∩ allowlist (`core.agent_tool_permission`); fuera de la lista = `denied` auditado |
| Decisión | Reglas en código (`domain/rules.py`); el LLM interpreta y redacta, no decide umbrales |
| Estado | Checkpointer PostgreSQL (`thread_id = onboarding_id`); `interrupt()` + `Command(resume=…)` para la conversación |
| Fallas | Reintentos/timeout por tool (`core.tool`); crítico caído = `ERROR` con código específico (fail-closed); no crítico = fallback RAG |
| PII | La cédula se inyecta desde el estado: nunca llega al LLM; auditoría enmascarada (`171234****`) |
| Mensajes | Plantilla aprobada + LLM; guardrails (términos prohibidos, código, canales de ayuda); riesgo alto solo plantilla |

Módulos: `backend/app/{agents,graph,tools,rag,domain,contracts,services,api,provisioning}`.
