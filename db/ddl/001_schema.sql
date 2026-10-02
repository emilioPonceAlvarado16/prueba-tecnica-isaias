-- =============================================================================
-- PROPUESTA DDL - Onboarding Digital Multi-Agente (PoC)
-- Estado: APROBADO 2026-10-02
-- Motor: PostgreSQL 16 + pgvector 0.7+
--
-- Esquemas:
--   core        -> datos transaccionales del onboarding, catálogos, permisos de agentes, auditoría
--   ext         -> simulación (mock) de sistemas externos: Registro Civil, listas de riesgo
--   rag         -> documentos de políticas, chunks + embeddings, catálogo semántico de tools
--   checkpoint  -> tablas del checkpointer de LangGraph (las crea langgraph-checkpoint-postgres)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- similitud de nombres (match de listas / identidad)
CREATE EXTENSION IF NOT EXISTS unaccent;   -- normalizar tildes (José == Jose)

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS ext;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS checkpoint;

-- unaccent() no es IMMUTABLE; wrapper inmutable para poder indexar
CREATE OR REPLACE FUNCTION core.normalize_name(txt text)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
$$ SELECT lower(public.unaccent('public.unaccent'::regdictionary, trim(regexp_replace(txt, '\s+', ' ', 'g')))) $$;

-- =============================================================================
-- ESQUEMA core
-- =============================================================================

CREATE TYPE core.onboarding_status AS ENUM (
    'RECEIVED',            -- recibido, aún no procesado
    'IN_PROGRESS',         -- grafo en ejecución
    'AWAITING_CUSTOMER',   -- interrupt de LangGraph: se pidió información al cliente
    'APPROVED',            -- apto, usuario provisionado
    'APPROVED_PENDING_PROVISIONING', -- apto, pero falló la creación del usuario (reintento)
    'REJECTED',            -- no apto
    'ESCALATED',           -- requiere intervención humana (agencia / cumplimiento)
    'ERROR'                -- falla técnica de un tool crítico
);

CREATE TYPE core.risk_level AS ENUM ('low', 'medium', 'high');

CREATE TYPE core.step_status AS ENUM ('ok', 'failed', 'escalated', 'skipped');

CREATE TYPE core.tool_call_status AS ENUM ('success', 'error', 'timeout', 'denied');

-- ---------------------------------------------------------------------------
-- Catálogos de producto y documentación
-- ---------------------------------------------------------------------------
CREATE TABLE core.product (
    code               varchar(40)  PRIMARY KEY,           -- 'cuenta_ahorros'
    name               varchar(120) NOT NULL,
    description        text,
    min_age            smallint     NOT NULL DEFAULT 18,
    digital_onboarding boolean      NOT NULL DEFAULT true,  -- ¿se puede abrir 100% en línea?
    active             boolean      NOT NULL DEFAULT true,
    policy_ref         varchar(40),                         -- 'POL-PRD-003'
    created_at         timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE core.document_type (
    code        varchar(40)  PRIMARY KEY,                   -- 'CEDULA', 'PLANILLA_SERVICIO_BASICO'
    name        varchar(160) NOT NULL,
    description text
);

-- Qué documentos exige cada producto y bajo qué condición (consumido por prepare_documentation)
CREATE TABLE core.product_document_requirement (
    product_code  varchar(40) NOT NULL REFERENCES core.product(code),
    document_code varchar(40) NOT NULL REFERENCES core.document_type(code),
    condition     varchar(30) NOT NULL DEFAULT 'always'
                  CHECK (condition IN ('always', 'risk_medium', 'risk_high', 'pep')),
    mandatory     boolean     NOT NULL DEFAULT true,
    policy_ref    varchar(40),                              -- artículo de la política que lo exige
    PRIMARY KEY (product_code, document_code, condition)
);

-- ---------------------------------------------------------------------------
-- Agentes, tools y permisos (el orquestador controla qué tool puede usar cada agente)
-- ---------------------------------------------------------------------------
CREATE TABLE core.agent (
    code          varchar(40) PRIMARY KEY,                  -- 'identity_agent'
    name          varchar(120) NOT NULL,
    description   text NOT NULL,
    system_prompt text NOT NULL,
    model         varchar(60) NOT NULL,
    temperature   numeric(3,2) NOT NULL DEFAULT 0,
    active        boolean NOT NULL DEFAULT true
);

CREATE TABLE core.tool (
    code          varchar(60) PRIMARY KEY,                  -- 'verify_identity'
    description   text        NOT NULL,                     -- también se embebe en rag.tool_embedding
    input_schema  jsonb       NOT NULL,                     -- JSON Schema derivado del contrato marshmallow
    is_critical   boolean     NOT NULL DEFAULT true,        -- si falla y es crítico -> status ERROR (fail-closed)
    timeout_ms    integer     NOT NULL DEFAULT 3000 CHECK (timeout_ms > 0),
    max_retries   smallint    NOT NULL DEFAULT 2 CHECK (max_retries BETWEEN 0 AND 5),
    error_code    varchar(20) NOT NULL,                     -- código mostrado al usuario si no responde: 'ONB-IDV-503'
    active        boolean     NOT NULL DEFAULT true
);

-- Allowlist: un agente SOLO puede ejecutar los tools listados aquí.
CREATE TABLE core.agent_tool_permission (
    agent_code varchar(40) NOT NULL REFERENCES core.agent(code),
    tool_code  varchar(60) NOT NULL REFERENCES core.tool(code),
    granted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_code, tool_code)
);

-- ---------------------------------------------------------------------------
-- Onboarding (cabecera) + traza de pasos + tool calls + conversación
-- ---------------------------------------------------------------------------
CREATE TABLE core.onboarding_request (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_name     varchar(160) NOT NULL,
    document_id       char(10)     NOT NULL CHECK (document_id ~ '^[0-9]{10}$'),
    product_code      varchar(40)  NOT NULL REFERENCES core.product(code),
    email             varchar(254),                         -- opcional (ver decisión D3)
    status            core.onboarding_status NOT NULL DEFAULT 'RECEIVED',
    reason_code       varchar(20),                          -- 'ONB-IDV-002'
    risk_level        core.risk_level,
    identity_confidence numeric(4,3) CHECK (identity_confidence BETWEEN 0 AND 1),
    customer_message  text,                                 -- mensaje final generado por response_agent
    proposed_solution text,                                 -- solución propuesta si falla / es ambiguo
    required_documents jsonb NOT NULL DEFAULT '[]'::jsonb,
    thread_id         varchar(80)  NOT NULL UNIQUE,         -- thread de LangGraph (= id del checkpoint)
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),
    completed_at      timestamptz
);

-- Evita dos onboardings activos/aprobados para la misma cédula y producto (-> HTTP 409)
CREATE UNIQUE INDEX ux_onboarding_active_per_document_product
    ON core.onboarding_request (document_id, product_code)
    WHERE status IN ('RECEIVED', 'IN_PROGRESS', 'AWAITING_CUSTOMER', 'APPROVED', 'APPROVED_PENDING_PROVISIONING');

CREATE INDEX ix_onboarding_status_created ON core.onboarding_request (status, created_at DESC);

-- Una fila por nodo del grafo ejecutado (traza visible en el frontend)
CREATE TABLE core.onboarding_step (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    onboarding_id uuid NOT NULL REFERENCES core.onboarding_request(id) ON DELETE CASCADE,
    node_name     varchar(60) NOT NULL,                     -- 'identity_agent', 'decision', ...
    agent_code    varchar(40) REFERENCES core.agent(code),
    status        core.step_status NOT NULL,
    summary       text,                                     -- resumen legible para la UI
    output        jsonb,                                    -- salida validada por marshmallow
    started_at    timestamptz NOT NULL,
    finished_at   timestamptz,
    duration_ms   integer GENERATED ALWAYS AS
                  ((EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::integer) STORED
);
CREATE INDEX ix_step_onboarding ON core.onboarding_step (onboarding_id, started_at);

-- Auditoría de cada invocación de tool (incluye intentos denegados por permisos)
CREATE TABLE core.tool_call_log (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    onboarding_id uuid NOT NULL REFERENCES core.onboarding_request(id) ON DELETE CASCADE,
    agent_code    varchar(40) NOT NULL REFERENCES core.agent(code),
    tool_code     varchar(60) NOT NULL,                     -- sin FK: se registra aunque el tool no exista (denied)
    args_masked   jsonb NOT NULL,                           -- cédula enmascarada: 171234****
    result        jsonb,
    status        core.tool_call_status NOT NULL,
    attempt       smallint NOT NULL DEFAULT 1,
    latency_ms    integer,
    error_message text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_toolcall_onboarding ON core.tool_call_log (onboarding_id, created_at);

-- Estado conversacional persistido en negocio (el estado técnico vive en checkpoint.*)
CREATE TABLE core.onboarding_message (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    onboarding_id uuid NOT NULL REFERENCES core.onboarding_request(id) ON DELETE CASCADE,
    role          varchar(12) NOT NULL CHECK (role IN ('customer', 'assistant', 'system')),
    content       text  NOT NULL,
    payload       jsonb,                                    -- p.ej. respuestas estructuradas del cliente
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_message_onboarding ON core.onboarding_message (onboarding_id, created_at);

CREATE TABLE core.escalation (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    onboarding_id     uuid NOT NULL REFERENCES core.onboarding_request(id) ON DELETE CASCADE,
    reason_code       varchar(20) NOT NULL,
    queue             varchar(20) NOT NULL CHECK (queue IN ('agencia', 'cumplimiento', 'soporte_ti')),
    proposed_solution text NOT NULL,
    status            varchar(12) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'discarded')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    resolved_at       timestamptz
);
CREATE INDEX ix_escalation_open ON core.escalation (queue) WHERE status = 'open';

-- Resultado de la provisión del usuario (local: mock; AWS: Lambda -> Cognito)
CREATE TABLE core.provisioned_user (
    onboarding_id   uuid PRIMARY KEY REFERENCES core.onboarding_request(id) ON DELETE CASCADE,
    document_id     char(10)    NOT NULL UNIQUE,
    username        varchar(128) NOT NULL,
    provider        varchar(20) NOT NULL CHECK (provider IN ('local_mock', 'cognito')),
    external_id     varchar(128),                           -- cognito sub
    status          varchar(20) NOT NULL CHECK (status IN ('created', 'failed')),
    error_message   text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Ejemplos de respuesta ideal por escenario (few-shot del response_agent / dataset de fine-tuning)
CREATE TABLE core.response_example (
    id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reason_code   varchar(20) NOT NULL,
    context       jsonb NOT NULL,                           -- entrada resumida que vio el agente
    ideal_message text  NOT NULL
);
CREATE INDEX ix_response_example_reason ON core.response_example (reason_code);

-- =============================================================================
-- ESQUEMA ext  (mocks de sistemas externos, datos dummy en BD real)
-- =============================================================================

-- Simula el servicio de Registro Civil del Ecuador
CREATE TABLE ext.registro_civil (
    document_id       char(10) PRIMARY KEY CHECK (document_id ~ '^[0-9]{10}$'),
    nombres           varchar(80)  NOT NULL,
    apellidos         varchar(80)  NOT NULL,
    nombre_completo   varchar(160) GENERATED ALWAYS AS (nombres || ' ' || apellidos) STORED,
    fecha_nacimiento  date NOT NULL,
    lugar_nacimiento  varchar(80),
    estado_civil      varchar(20),
    condicion         varchar(20) NOT NULL DEFAULT 'CIUDADANO'
                      CHECK (condicion IN ('CIUDADANO', 'FALLECIDO', 'CEDULA_ANULADA')),
    calidad_dato      numeric(3,2) NOT NULL CHECK (calidad_dato BETWEEN 0 AND 1),  -- -> confidence del tool
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ext.risk_list (
    code      varchar(30) PRIMARY KEY,                      -- 'OFAC_SDN', 'ONU_CSNU', 'UAFE', 'PEP_EC', 'INTERNA'
    name      varchar(160) NOT NULL,
    source    varchar(160) NOT NULL,
    severity  core.risk_level NOT NULL                      -- nivel que aporta un match en esta lista
);

CREATE TABLE ext.risk_list_entry (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    list_code    varchar(30) NOT NULL REFERENCES ext.risk_list(code),
    document_id  char(10),                                  -- puede no tenerse (listas internacionales)
    full_name    varchar(160) NOT NULL,
    aliases      text[] NOT NULL DEFAULT '{}',
    reason       text,
    active       boolean NOT NULL DEFAULT true,
    added_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_risk_entry_document ON ext.risk_list_entry (document_id) WHERE active;
CREATE INDEX ix_risk_entry_name_trgm ON ext.risk_list_entry
    USING gin (core.normalize_name(full_name) gin_trgm_ops) WHERE active;

-- Inyección determinística de fallas para probar "tool importante no responde"
CREATE TABLE ext.service_fault (
    tool_code   varchar(60) NOT NULL,
    document_id char(10)    NOT NULL,
    fault_type  varchar(20) NOT NULL CHECK (fault_type IN ('timeout', 'error_500')),
    PRIMARY KEY (tool_code, document_id)
);

-- =============================================================================
-- ESQUEMA rag
-- Embeddings: OpenAI text-embedding-3-small (1536 dims). Distancia coseno (<=>).
-- =============================================================================

CREATE TABLE rag.source_document (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code           varchar(40)  NOT NULL,                   -- 'POL-KYC-001'
    title          varchar(200) NOT NULL,
    version        varchar(20)  NOT NULL,
    source_type    varchar(10)  NOT NULL CHECK (source_type IN ('pdf', 'md', 'txt')),
    file_name      varchar(255) NOT NULL,
    sha256         char(64)     NOT NULL UNIQUE,            -- re-ingesta idempotente
    effective_date date         NOT NULL,
    metadata       jsonb        NOT NULL DEFAULT '{}'::jsonb,
    ingested_at    timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (code, version)
);

CREATE TABLE rag.policy_chunk (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   uuid NOT NULL REFERENCES rag.source_document(id) ON DELETE CASCADE,
    chunk_index   integer NOT NULL,
    section_path  text    NOT NULL,                         -- 'POL-PLA-002 > Art. 5 > Personas Expuestas Políticamente'
    content       text    NOT NULL,
    token_count   integer NOT NULL,
    embedding     vector(1536) NOT NULL,
    metadata      jsonb   NOT NULL DEFAULT '{}'::jsonb,     -- {"products":["cuenta_ahorros"], "topics":["pep"]}
    UNIQUE (document_id, chunk_index)
);

-- El índice IVFFLAT (coseno) se crea en 002_vector_index.sql DESPUÉS de la ingesta:
-- los centroides se calculan con los datos existentes; creado sobre tabla vacía queda inútil.
CREATE INDEX ix_policy_chunk_metadata ON rag.policy_chunk USING gin (metadata jsonb_path_ops);

-- "RAG para saber qué tool calls usar": descripción semántica de cada tool
CREATE TABLE rag.tool_embedding (
    tool_code    varchar(60) PRIMARY KEY,                   -- referencia lógica a core.tool (esquemas desacoplados)
    description  text NOT NULL,
    usage_examples text[] NOT NULL DEFAULT '{}',
    embedding    vector(1536) NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);
-- Sin índice ANN: con < 50 filas el scan exacto es más rápido y con recall 100%.

-- Observabilidad del retrieval (para ajustar lists/probes con evidencia)
CREATE TABLE rag.retrieval_log (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    onboarding_id uuid,                                     -- referencia lógica a core.onboarding_request
    agent_code    varchar(40) NOT NULL,
    query_text    text NOT NULL,
    top_k         smallint NOT NULL,
    probes        smallint,
    results       jsonb NOT NULL,                           -- [{"chunk_id":1,"score":0.83}, ...]
    latency_ms    integer,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- ESQUEMA checkpoint
-- Lo puebla langgraph-checkpoint-postgres (PostgresSaver.setup()) con search_path=checkpoint:
--   checkpoint.checkpoints, checkpoint.checkpoint_blobs, checkpoint.checkpoint_writes, checkpoint.checkpoint_migrations
-- No se definen a mano para no desalinearse con la versión de la librería.
-- =============================================================================

-- =============================================================================
-- Roles (mínimo privilegio)
-- =============================================================================
-- CREATE ROLE onboarding_app LOGIN PASSWORD '***';
-- GRANT USAGE ON SCHEMA core, ext, rag, checkpoint TO onboarding_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core TO onboarding_app;
-- GRANT SELECT ON ALL TABLES IN SCHEMA ext TO onboarding_app;          -- mocks: solo lectura
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA rag TO onboarding_app;   -- ingesta usa rol aparte
-- GRANT ALL ON SCHEMA checkpoint TO onboarding_app;
