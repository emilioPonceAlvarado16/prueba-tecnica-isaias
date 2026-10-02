# API v1

Swagger: `http://localhost:8010/api/v1/docs` · Contratos marshmallow: `backend/app/contracts/`

| Método | Ruta | Respuestas |
|---|---|---|
| POST | `/api/v1/onboarding/start` `{"prospect_name","document_id","product","email"?}` | 200 resultado · 400 `ONB-VAL-400` · 409 `ONB-DUP-409` · 503 tool crítico caído |
| GET | `/api/v1/onboarding/{id}` | 200 resultado + `messages` · 404 |
| POST | `/api/v1/onboarding/{id}/continue` `{"answers":{"actividad_economica","origen_fondos","ingresos_mensuales"}}` | 200 · 409 si no está en `AWAITING_CUSTOMER` |
| GET | `/api/v1/products` · `/api/v1/health` | 200 |

Resultado: `onboarding_id, status, reason_code, customer_message, proposed_solution, next_action{type}, required_documents[], pending_questions[], agents_trace[], provisioning{username, temporary_password (solo en la respuesta inmediata, modo demo)}, error{code,message}`.

| Código | Estado | Significado |
|---|---|---|
| ONB-OK-000 / 001 | APPROVED | Apto / apto tras debida diligencia reforzada |
| ONB-DOC-001 | REJECTED | Cédula inválida (módulo 10) |
| ONB-IDV-001 / 002 / 003 | ESCALATED | No verificado / confianza < 0.80 / nombre no coincide → agencia |
| ONB-IDV-004 | REJECTED | Menor de edad |
| ONB-RSK-001 | ESCALATED | Riesgo alto → cumplimiento (mensaje genérico) |
| ONB-RSK-002 | AWAITING_CUSTOMER | Riesgo medio (PEP): pide información |
| ONB-IDV-503 / ONB-RSK-503 | ERROR (HTTP 503) | Registro Civil / listas no responden |
| ONB-PRV-503 | APPROVED_PENDING_PROVISIONING | Aprobado, falló la creación del usuario |
