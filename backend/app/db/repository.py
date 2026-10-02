"""Acceso a datos del esquema core (y lecturas de ext para los tools)."""
from datetime import datetime
from functools import lru_cache

from psycopg.types.json import Jsonb

from app.db.pool import execute, fetch_all, fetch_one

ACTIVE_STATUSES = ("RECEIVED", "IN_PROGRESS", "AWAITING_CUSTOMER", "APPROVED", "APPROVED_PENDING_PROVISIONING")


# ----------------------------------------------------------------- catálogos
def active_product_codes() -> set[str]:
    return {r["code"] for r in fetch_all("SELECT code FROM core.product WHERE active AND digital_onboarding")}


def list_products() -> list[dict]:
    return fetch_all("SELECT code, name, description FROM core.product WHERE active ORDER BY code")


def get_product(code: str) -> dict | None:
    return fetch_one("SELECT * FROM core.product WHERE code = %s", (code,))


@lru_cache(maxsize=16)
def get_agent(code: str) -> dict:
    return fetch_one("SELECT * FROM core.agent WHERE code = %s", (code,))


@lru_cache(maxsize=16)
def get_tool(code: str) -> dict | None:
    return fetch_one("SELECT * FROM core.tool WHERE code = %s AND active", (code,))


@lru_cache(maxsize=16)
def allowed_tools(agent_code: str) -> frozenset[str]:
    rows = fetch_all("""SELECT p.tool_code FROM core.agent_tool_permission p
                        JOIN core.tool t ON t.code = p.tool_code AND t.active WHERE p.agent_code = %s""", (agent_code,))
    return frozenset(r["tool_code"] for r in rows)


def response_examples(reason_code: str, limit: int = 2) -> list[dict]:
    rows = fetch_all("SELECT context, ideal_message FROM core.response_example WHERE reason_code = %s LIMIT %s",
                     (reason_code, limit))
    if not rows:
        rows = fetch_all("SELECT context, ideal_message FROM core.response_example ORDER BY id LIMIT %s", (limit,))
    return rows


# ----------------------------------------------------------------- onboarding
def find_active_onboarding(document_id: str, product: str) -> dict | None:
    return fetch_one("""SELECT id, status FROM core.onboarding_request
                        WHERE document_id = %s AND product_code = %s AND status = ANY(%s::core.onboarding_status[])
                        ORDER BY created_at DESC LIMIT 1""", (document_id, product, list(ACTIVE_STATUSES)))


def create_onboarding(onboarding_id: str, data: dict) -> None:
    execute("""INSERT INTO core.onboarding_request (id, prospect_name, document_id, product_code, email, status, thread_id)
               VALUES (%s, %s, %s, %s, %s, 'IN_PROGRESS', %s)""",
            (onboarding_id, data["prospect_name"], data["document_id"], data["product"], data.get("email"), onboarding_id))


def update_onboarding(onboarding_id: str, **fields) -> None:
    if not fields:
        return
    if "required_documents" in fields:
        fields["required_documents"] = Jsonb(fields["required_documents"])
    assignments = ", ".join(f"{k} = %({k})s" for k in fields)
    execute(f"UPDATE core.onboarding_request SET {assignments}, updated_at = now() WHERE id = %(id)s",
            {**fields, "id": onboarding_id})


def get_onboarding(onboarding_id: str) -> dict | None:
    return fetch_one("SELECT * FROM core.onboarding_request WHERE id = %s", (onboarding_id,))


def get_steps(onboarding_id: str) -> list[dict]:
    return fetch_all("""SELECT node_name AS node, agent_code AS agent, status::text, summary, started_at, duration_ms
                        FROM core.onboarding_step WHERE onboarding_id = %s ORDER BY started_at, id""", (onboarding_id,))


def insert_step(onboarding_id: str, node: str, agent: str | None, status: str, summary: str,
                output: dict | None, started_at: datetime, finished_at: datetime) -> None:
    execute("""INSERT INTO core.onboarding_step (onboarding_id, node_name, agent_code, status, summary, output, started_at, finished_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (onboarding_id, node, agent, status, summary, Jsonb(output) if output is not None else None,
             started_at, finished_at))


def insert_tool_call(onboarding_id: str, agent: str, tool: str, args_masked: dict, result: dict | None,
                     status: str, attempt: int, latency_ms: int | None, error: str | None) -> None:
    execute("""INSERT INTO core.tool_call_log (onboarding_id, agent_code, tool_code, args_masked, result, status, attempt, latency_ms, error_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (onboarding_id, agent, tool, Jsonb(args_masked), Jsonb(result) if result is not None else None,
             status, attempt, latency_ms, error))


def insert_message(onboarding_id: str, role: str, content: str, payload: dict | None = None) -> None:
    execute("INSERT INTO core.onboarding_message (onboarding_id, role, content, payload) VALUES (%s, %s, %s, %s)",
            (onboarding_id, role, content, Jsonb(payload) if payload is not None else None))


def get_messages(onboarding_id: str) -> list[dict]:
    return fetch_all("""SELECT role, content, created_at FROM core.onboarding_message
                        WHERE onboarding_id = %s ORDER BY created_at, id""", (onboarding_id,))


def insert_escalation(onboarding_id: str, reason_code: str, queue: str, proposed_solution: str) -> None:
    execute("""INSERT INTO core.escalation (onboarding_id, reason_code, queue, proposed_solution)
               VALUES (%s, %s, %s, %s)""", (onboarding_id, reason_code, queue, proposed_solution))


def get_provisioned_user(onboarding_id: str) -> dict | None:
    return fetch_one("SELECT * FROM core.provisioned_user WHERE onboarding_id = %s", (onboarding_id,))


def get_provisioned_by_document(document_id: str) -> dict | None:
    return fetch_one("SELECT * FROM core.provisioned_user WHERE document_id = %s AND status = 'created'", (document_id,))


def save_provisioned_user(onboarding_id: str, document_id: str, username: str, provider: str,
                          external_id: str | None, status: str, error: str | None) -> None:
    execute("""INSERT INTO core.provisioned_user (onboarding_id, document_id, username, provider, external_id, status, error_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (onboarding_id) DO UPDATE SET status = EXCLUDED.status, error_message = EXCLUDED.error_message,
                   external_id = EXCLUDED.external_id""",
            (onboarding_id, document_id, username, provider, external_id, status, error))


# ----------------------------------------------------------------- ext (mocks)
def service_fault(tool_code: str, document_id: str) -> str | None:
    row = fetch_one("SELECT fault_type FROM ext.service_fault WHERE tool_code = %s AND document_id = %s",
                    (tool_code, document_id))
    return row["fault_type"] if row else None
