"""Nodos del orquestador que no son agentes LLM: validación, interrupt, decisión, provisión y cierre."""
from langgraph.types import interrupt

from app.db import repository
from app.domain.cedula import validate_cedula
from app.domain.error_codes import outcome
from app.graph.tracing import now, record_step
from app.provisioning import provision
from app.tools.errors import ToolError
from app.tools.faults import raise_if_faulty

CUSTOMER_QUESTIONS = [
    {"field": "actividad_economica", "label": "Actividad económica principal", "type": "select", "required": True,
     "options": ["Empleado privado", "Empleado público", "Independiente / profesional", "Comerciante",
                 "Jubilado", "Otra"]},
    {"field": "origen_fondos", "label": "Origen de los fondos", "type": "select", "required": True,
     "options": ["Sueldo", "Honorarios profesionales", "Ventas de negocio propio", "Herencia o donación",
                 "Rendimientos de inversiones", "Otro"]},
    {"field": "ingresos_mensuales", "label": "Ingresos mensuales estimados (USD)", "type": "number",
     "required": True, "options": None},
]


def validate_input_node(state: dict) -> dict:
    started = now()
    check = validate_cedula(state["request"]["document_id"])
    summary = "Cédula válida (provincia, tercer dígito y módulo 10)" if check.valid else f"Cédula inválida: {check.reason}"
    trace = record_step(state, "validate_input", "orchestrator", "ok" if check.valid else "failed", summary, started)
    return {"cedula_valid": check.valid, "outcome_code": None if check.valid else "ONB-DOC-001", "trace": [trace]}


def request_customer_info_node(state: dict) -> dict:
    """Riesgo medio: pausa el grafo (checkpoint en PostgreSQL) hasta que el cliente responda vía /continue."""
    answers = interrupt({"reason_code": "ONB-RSK-002", "questions": CUSTOMER_QUESTIONS})
    started = now()
    summary = (f"Cliente completó debida diligencia reforzada: {answers['actividad_economica']}, "
               f"fondos de {answers['origen_fondos'].lower()}")
    trace = record_step(state, "request_customer_info", "orchestrator", "ok", summary, started,
                        {"answers": answers})
    return {"customer_inputs": answers, "edd": True, "outcome_code": None, "trace": [trace]}


def decision_node(state: dict) -> dict:
    started = now()
    code = state.get("outcome_code") or ("ONB-OK-001" if state.get("edd") else "ONB-OK-000")
    rule = outcome(code)
    decision = {"code": code, "status": rule.status, "next_action": rule.next_action, "queue": rule.queue,
                "proposed_solution": rule.proposed_solution, "policy_ref": rule.policy_ref}
    summary = f"{rule.status} · {code} · fundamento {rule.policy_ref}" + (f" · cola {rule.queue}" if rule.queue else "")
    status = {"APPROVED": "ok", "ESCALATED": "escalated"}.get(rule.status, "failed")
    trace = record_step(state, "decision", "orchestrator", status, summary, started, {"decision": decision})
    return {"decision": decision, "trace": [trace]}


def provision_user_node(state: dict) -> dict:
    started = now()
    request, identity = state["request"], state.get("identity") or {}
    try:
        raise_if_faulty("provision_user", request["document_id"])
        result = provision(state["onboarding_id"], request["document_id"],
                           identity.get("registered_name") or request["prospect_name"], request["product"],
                           request.get("email"))
        summary = (f"Usuario {'existente reutilizado' if result.get('existing') else 'creado'} "
                   f"({result['provider']}), usuario = cédula")
        trace = record_step(state, "provision_user", "orchestrator", "ok", summary, started,
                            {"provider": result["provider"], "existing": bool(result.get("existing"))})
        return {"provisioning": result, "trace": [trace]}
    except (ToolError, Exception) as exc:  # noqa: BLE001 - la cuenta queda aprobada, el acceso se reintenta
        repository.save_provisioned_user(state["onboarding_id"], request["document_id"], request["document_id"],
                                         "cognito" if "lambda" in type(exc).__module__ else "local_mock",
                                         None, "failed", str(exc)[:500])
        rule = outcome("ONB-PRV-503")
        decision = {**state["decision"], "code": rule.code, "status": rule.status, "next_action": rule.next_action,
                    "queue": rule.queue, "proposed_solution": rule.proposed_solution, "policy_ref": rule.policy_ref}
        trace = record_step(state, "provision_user", "orchestrator", "failed",
                            f"Falló la creación del usuario: {exc} → ONB-PRV-503", started)
        return {"provisioning": {"status": "failed", "provider": "local_mock", "username": request["document_id"],
                                 "temporary_password": None},
                "decision": decision, "trace": [trace]}


def finalize_node(state: dict) -> dict:
    started = now()
    decision, identity, risk = state["decision"], state.get("identity") or {}, state.get("risk") or {}
    documents = (state.get("documentation") or {}).get("required_documents", []) \
        if decision["status"].startswith("APPROVED") else []
    repository.update_onboarding(
        state["onboarding_id"],
        status=decision["status"],
        reason_code=decision["code"],
        risk_level=risk.get("risk_level"),
        identity_confidence=identity.get("confidence"),
        customer_message=state["customer_message"],
        proposed_solution=decision["proposed_solution"],
        required_documents=documents,
        completed_at=now(),
    )
    if decision["queue"]:
        repository.insert_escalation(state["onboarding_id"], decision["code"], decision["queue"],
                                     decision["proposed_solution"])
    repository.insert_message(state["onboarding_id"], "assistant", state["customer_message"],
                              {"reason_code": decision["code"]})
    trace = record_step(state, "finalize", "orchestrator", "ok",
                        f"Estado final {decision['status']} persistido" +
                        (f"; escalamiento a {decision['queue']}" if decision["queue"] else ""), started)
    return {"trace": [trace]}
