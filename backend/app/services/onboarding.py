"""Casos de uso: iniciar, continuar y consultar un onboarding (orquesta el grafo y arma la respuesta)."""
import logging
import uuid

from langgraph.types import Command
from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import repository
from app.domain.cedula import mask
from app.domain.error_codes import outcome
from app.domain.names import first_name
from app.graph.builder import get_graph
from app.graph.nodes import CUSTOMER_QUESTIONS
from app.graph.tracing import now, record_step

log = logging.getLogger(__name__)


class DuplicateOnboarding(Exception):
    def __init__(self, onboarding_id: str):
        self.onboarding_id = onboarding_id


class NotAwaitingCustomer(Exception):
    pass


def _config(onboarding_id: str) -> dict:
    return {"configurable": {"thread_id": onboarding_id}}


def start(data: dict) -> tuple[dict, int]:
    existing = repository.find_active_onboarding(data["document_id"], data["product"])
    if existing:
        raise DuplicateOnboarding(str(existing["id"]))
    onboarding_id = str(uuid.uuid4())
    try:
        repository.create_onboarding(onboarding_id, data)
    except UniqueViolation:
        existing = repository.find_active_onboarding(data["document_id"], data["product"])
        raise DuplicateOnboarding(str(existing["id"]) if existing else onboarding_id)
    repository.insert_message(onboarding_id, "customer", f"Solicitud de apertura: {data['product']}",
                              {"product": data["product"], "document_id": mask(data["document_id"])})
    request = {k: data.get(k) for k in ("prospect_name", "document_id", "product", "email")}
    return _run(onboarding_id, {"onboarding_id": onboarding_id, "request": request})


def resume(onboarding_id: str, answers: dict) -> tuple[dict, int]:
    row = repository.get_onboarding(onboarding_id)
    if row is None:
        raise LookupError(onboarding_id)
    if row["status"] != "AWAITING_CUSTOMER":
        raise NotAwaitingCustomer(row["status"])
    repository.insert_message(onboarding_id, "customer", "Información adicional enviada", answers)
    repository.update_onboarding(onboarding_id, status="IN_PROGRESS")
    return _run(onboarding_id, Command(resume=answers))


def _run(onboarding_id: str, graph_input) -> tuple[dict, int]:
    try:
        state = get_graph().invoke(graph_input, _config(onboarding_id))
    except Exception:
        log.exception("Falla no controlada del grafo %s", onboarding_id)
        repository.update_onboarding(onboarding_id, status="ERROR", reason_code="ONB-SYS-500", completed_at=now(),
                                     customer_message="Tuvimos un problema procesando tu solicitud. Intenta nuevamente "
                                                      "en unos minutos o llama al 1800-ANDINO (1800-263466).")
        return get_result(onboarding_id), 500

    if state.get("__interrupt__"):
        _mark_awaiting(onboarding_id, state)
    result = get_result(onboarding_id)
    provisioning = state.get("provisioning")
    if provisioning and result.get("provisioning") and settings.demo_mode:
        # La contraseña temporal nunca se persiste: solo viaja en esta respuesta (modo demo)
        result["provisioning"]["temporary_password"] = provisioning.get("temporary_password")
    status_code = outcome(result["reason_code"]).http_status if result["reason_code"] in _codes() else 200
    return result, status_code


def _codes():
    from app.domain.error_codes import OUTCOMES
    return OUTCOMES


def _mark_awaiting(onboarding_id: str, state: dict) -> None:
    rule = outcome("ONB-RSK-002")
    request = state["request"]
    product = repository.get_product(request["product"])
    message = rule.template.format(first_name=first_name(request["prospect_name"]), product_name=product["name"])
    repository.update_onboarding(onboarding_id, status="AWAITING_CUSTOMER", reason_code=rule.code,
                                 risk_level=state["risk"]["risk_level"],
                                 identity_confidence=state["identity"]["confidence"],
                                 customer_message=message, proposed_solution=rule.proposed_solution)
    repository.insert_message(onboarding_id, "assistant", message, {"questions": [q["field"] for q in CUSTOMER_QUESTIONS]})
    record_step(state, "request_customer_info", "orchestrator", "escalated",
                "Grafo pausado (interrupt): esperando actividad económica, origen de fondos e ingresos", now())


def get_result(onboarding_id: str, include_messages: bool = False) -> dict | None:
    row = repository.get_onboarding(onboarding_id)
    if row is None:
        return None
    code = row["reason_code"]
    rule = _codes().get(code)
    status = row["status"]
    provisioned = repository.get_provisioned_user(onboarding_id)

    error = None
    if status == "ERROR" or (rule and rule.http_status >= 500):
        error = {"code": code or "ONB-SYS-500", "message": "Servicio no disponible temporalmente"}

    result = {
        "onboarding_id": row["id"],
        "status": status,
        "reason_code": code,
        "customer_message": row["customer_message"],
        "proposed_solution": row["proposed_solution"],
        "next_action": {"type": rule.next_action if rule else ("RETRY_LATER" if status == "ERROR" else "NONE"),
                        "detail": rule.queue if rule else None},
        "required_documents": row["required_documents"] or [],
        "pending_questions": CUSTOMER_QUESTIONS if status == "AWAITING_CUSTOMER" else [],
        "agents_trace": repository.get_steps(onboarding_id),
        "provisioning": ({"username": provisioned["username"], "provider": provisioned["provider"],
                          "status": provisioned["status"], "temporary_password": None} if provisioned else None),
        "error": error,
        "prospect_name": row["prospect_name"],
        "document_id_masked": mask(row["document_id"]),
        "product": row["product_code"],
        "created_at": row["created_at"],
    }
    if include_messages:
        result["messages"] = repository.get_messages(onboarding_id)
    return result
