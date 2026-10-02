#!/bin/bash

# Onboarding Digital Multi-Agente - Environment Manager
# Servicios: PostgreSQL + pgvector (Docker), API Flask/LangGraph (backend), Frontend Next.js (frontend)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
PID_DIR="${SCRIPT_DIR}/.pids"
LOG_DIR="${SCRIPT_DIR}/.logs"

PG_CONTAINER="onboarding-postgres"
PG_USER="onboarding"
PG_DB="onboarding"
API_PORT="${API_PORT:-8010}"
FRONTEND_PORT=3000

API_PID="${PID_DIR}/api.pid"
FRONTEND_PID="${PID_DIR}/frontend.pid"
API_LOG="${LOG_DIR}/api.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

mkdir -p "${PID_DIR}" "${LOG_DIR}"

print_info()    { echo -e "${BLUE}ℹ ${1}${NC}"; }
print_success() { echo -e "${GREEN}✓ ${1}${NC}"; }
print_error()   { echo -e "${RED}✗ ${1}${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ ${1}${NC}"; }
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  ${1}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
        rm -f "$pid_file"
    fi
    return 1
}

wait_for_http() {
    local url="$1" name="$2"
    for _ in $(seq 1 60); do
        if curl -s -o /dev/null "$url"; then
            return 0
        fi
        sleep 1
    done
    print_error "${name} no respondió en ${url}"
    return 1
}

psql_exec() {
    docker exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -q -U "$PG_USER" -d "$PG_DB" "$@"
}

check_env_file() {
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        print_error "No existe .env. Copia .env.example a .env y coloca tu OPENAI_API_KEY."
        exit 1
    fi
}

# ------------------------------------------------------------------ Docker / PostgreSQL
start_docker() {
    if docker info > /dev/null 2>&1; then
        return 0
    fi
    if command -v colima &> /dev/null; then
        print_info "Iniciando Colima..."
        colima start > /dev/null 2>&1
        for _ in $(seq 1 30); do
            docker info > /dev/null 2>&1 && return 0
            sleep 1
        done
    fi
    print_error "Docker no está corriendo (inicia Docker Desktop o instala Colima: brew install colima)"
    return 1
}

start_db() {
    print_info "Iniciando PostgreSQL + pgvector (Docker)..."
    start_docker
    (cd "$SCRIPT_DIR" && docker compose up -d postgres > /dev/null 2>&1)
    for _ in $(seq 1 30); do
        if docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; then
            print_success "PostgreSQL listo (contenedor ${PG_CONTAINER}, puerto 5433)"
            return 0
        fi
        sleep 1
    done
    print_error "PostgreSQL no quedó listo"
    return 1
}

stop_db() {
    print_info "Deteniendo PostgreSQL..."
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^${PG_CONTAINER}$"; then
        docker stop "$PG_CONTAINER" > /dev/null
        print_success "PostgreSQL detenido (los datos se conservan en el volumen)"
    else
        print_warning "PostgreSQL no estaba corriendo"
    fi
}

db_init() {
    print_header "Inicializando base de datos (DDL + seeds)"
    start_db
    local exists
    exists=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name='core'")
    if [ "$exists" = "1" ]; then
        print_warning "El esquema ya existe; solo se aplican seeds (idempotentes). Usa db:reset para recrear."
    else
        psql_exec < "${SCRIPT_DIR}/db/ddl/001_schema.sql"
        print_success "DDL aplicado (esquemas core, ext, rag, checkpoint)"
    fi
    for seed in "${SCRIPT_DIR}"/db/seeds/*.sql; do
        psql_exec < "$seed"
        print_success "Seed $(basename "$seed")"
    done
}

db_reset() {
    print_header "Recreando base de datos"
    read -r -p "Esto BORRA todos los datos locales. ¿Continuar? (s/N) " answer
    [ "$answer" = "s" ] || { print_warning "Cancelado"; return 0; }
    start_db
    psql_exec -c "DROP SCHEMA IF EXISTS core, ext, rag, checkpoint CASCADE;"
    db_init
    rag_ingest
}

# ------------------------------------------------------------------ RAG
rag_ingest() {
    print_header "Pipeline RAG: PDFs -> chunking -> embeddings -> pgvector"
    check_env_file
    (cd "$BACKEND_DIR" && uv run python ../policies/build_pdfs.py && uv run python -m app.rag.ingest "$@")
}

rag_eval() {
    print_header "Evaluación RAG (recall@4, chunking fijo vs híbrido, IVFFLAT vs exacto)"
    (cd "$BACKEND_DIR" && uv run python -m app.rag.eval_recall)
}

# ------------------------------------------------------------------ API
start_api() {
    print_info "Iniciando API (Flask + LangGraph) en :${API_PORT}..."
    check_env_file
    if is_running "$API_PID"; then
        print_warning "La API ya está corriendo (PID $(cat "$API_PID"))"
        return 0
    fi
    (cd "$BACKEND_DIR" && uv sync -q)
    (cd "$BACKEND_DIR" && nohup uv run python -m app.main >> "$API_LOG" 2>&1 < /dev/null & echo $! > "$API_PID")
    if wait_for_http "http://localhost:${API_PORT}/api/v1/health" "API"; then
        print_success "API lista: http://localhost:${API_PORT}/api/v1/docs (Swagger)"
    fi
}

stop_api() {
    print_info "Deteniendo API..."
    if is_running "$API_PID"; then
        pkill -P "$(cat "$API_PID")" 2>/dev/null || true
        kill "$(cat "$API_PID")" 2>/dev/null || true
        rm -f "$API_PID"
        print_success "API detenida"
    else
        print_warning "La API no estaba corriendo"
    fi
    pkill -f "python -m app.main" 2>/dev/null || true
}

# ------------------------------------------------------------------ Frontend
start_frontend() {
    print_info "Iniciando frontend (Next.js) en :${FRONTEND_PORT}..."
    if is_running "$FRONTEND_PID"; then
        print_warning "El frontend ya está corriendo (PID $(cat "$FRONTEND_PID"))"
        return 0
    fi
    [ -d "${FRONTEND_DIR}/node_modules" ] || (cd "$FRONTEND_DIR" && npm install --silent)
    (cd "$FRONTEND_DIR" && nohup npm run dev >> "$FRONTEND_LOG" 2>&1 < /dev/null & echo $! > "$FRONTEND_PID")
    if wait_for_http "http://localhost:${FRONTEND_PORT}" "Frontend"; then
        print_success "Frontend listo: http://localhost:${FRONTEND_PORT}"
    fi
}

stop_frontend() {
    print_info "Deteniendo frontend..."
    if is_running "$FRONTEND_PID"; then
        pkill -P "$(cat "$FRONTEND_PID")" 2>/dev/null || true
        kill "$(cat "$FRONTEND_PID")" 2>/dev/null || true
        rm -f "$FRONTEND_PID"
        print_success "Frontend detenido"
    else
        print_warning "El frontend no estaba corriendo"
    fi
    pkill -f "next dev -p ${FRONTEND_PORT}" 2>/dev/null || true
}

# ------------------------------------------------------------------ Status / logs / tests
status() {
    print_header "Estado de servicios"
    if docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; then
        print_success "PostgreSQL     : corriendo (5433)"
    else
        print_error "PostgreSQL     : detenido"
    fi
    if curl -s "http://localhost:${API_PORT}/api/v1/health" > /dev/null 2>&1; then
        print_success "API            : corriendo (${API_PORT}) $(curl -s "http://localhost:${API_PORT}/api/v1/health")"
    else
        print_error "API            : detenida"
    fi
    if curl -s -o /dev/null "http://localhost:${FRONTEND_PORT}"; then
        print_success "Frontend       : corriendo (${FRONTEND_PORT})"
    else
        print_error "Frontend       : detenido"
    fi
}

logs() {
    case "$1" in
        api)      tail -f "$API_LOG" ;;
        frontend) tail -f "$FRONTEND_LOG" ;;
        db)       docker logs -f "$PG_CONTAINER" ;;
        *)        print_error "Uso: $0 logs {api|frontend|db}" ;;
    esac
}

run_tests() {
    print_header "Tests unitarios + integración (pytest)"
    (cd "$BACKEND_DIR" && uv run pytest -q)
}

run_scenarios() {
    print_header "Escenarios de usuarios de prueba (API en :${API_PORT})"
    (cd "$BACKEND_DIR" && uv run python scripts/run_scenarios.py "$@")
}

start_all() {
    print_header "Iniciando entorno local"
    start_db
    start_api
    start_frontend
    status
}

stop_all() {
    print_header "Deteniendo entorno local"
    stop_frontend
    stop_api
    stop_db
}

usage() {
    cat <<EOF
Uso: $0 <comando> [servicio]

  start [all|db|api|frontend]     Inicia servicios (por defecto todos)
  stop [all|db|api|frontend]      Detiene servicios
  restart [all|db|api|frontend]   Reinicia servicios
  status                          Estado de los servicios
  logs {api|frontend|db}          Sigue los logs

  setup                           Primera vez: db:init + rag:ingest + start all
  db:init                         Aplica DDL (si no existe) y seeds
  db:reset                        Borra y recrea todo (pide confirmación)
  rag:ingest [--force]            Genera PDFs de políticas e ingesta en pgvector
  rag:eval                        Evalúa el RAG y escribe docs/rag/EVALUACION_RAG.md
  test                            pytest
  scenarios [--reset --write-doc] Corre los 15 usuarios de prueba contra la API
EOF
}

service="${2:-all}"
case "$1" in
    start)
        case "$service" in
            all) start_all ;; db) start_db ;; api) start_api ;; frontend) start_frontend ;; *) usage ;;
        esac ;;
    stop)
        case "$service" in
            all) stop_all ;; db) stop_db ;; api) stop_api ;; frontend) stop_frontend ;; *) usage ;;
        esac ;;
    restart)
        case "$service" in
            all) stop_all; start_all ;;
            db) stop_db; start_db ;;
            api) stop_api; start_api ;;
            frontend) stop_frontend; start_frontend ;;
            *) usage ;;
        esac ;;
    status)     status ;;
    logs)       logs "$2" ;;
    setup)      db_init; rag_ingest; start_all ;;
    db:init)    db_init ;;
    db:reset)   db_reset ;;
    rag:ingest) shift; rag_ingest "$@" ;;
    rag:eval)   rag_eval ;;
    test)       run_tests ;;
    scenarios)  shift; run_scenarios "$@" ;;
    *)          usage ;;
esac
