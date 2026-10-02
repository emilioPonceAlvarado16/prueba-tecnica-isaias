"""Agente de Respuesta (POL-COM-005). Tool permitido: search_policies (acotado a la política del caso + POL-COM-005).

Few-shot dinámico (core.response_example) + fragmentos de política + plantilla aprobada como base.
Guardrails: si el mensaje del LLM rompe la política de comunicación se usa la plantilla.
Casos sensibles (riesgo alto) siempre usan plantilla: el LLM no redacta.
"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from marshmallow import Schema, ValidationError, fields, validate

from app.agents.base import chat_model
from app.agents.tool_gate import ToolGate
from app.config import settings
from app.db import repository
from app.domain.error_codes import outcome
from app.domain.names import first_name, normalize
from app.graph.tracing import now, record_step

AGENT = "response_agent"
FORBIDDEN = ["ofac", "uafe", "naciones unidas", "lista de control", "listas de control", "sancion", "lavado",
             "puntaje", "umbral", "oficial de cumplimiento", "confianza de", "0.8", "0,8", "monitoreo",
             "debida diligencia"]
MAX_WORDS = 140


CASE_GUIDANCE = {
    "APPROVED": "Felicita, confirma el usuario y lista los documentos con el plazo. No menciones controles internos.",
    "APPROVED_PENDING_PROVISIONING": "La cuenta está aprobada; el acceso digital estará listo en 24 horas.",
    "REJECTED": "Usa la frase 'por temas de políticas del banco', da la alternativa concreta y el código.",
    "ESCALATED": "Usa la frase 'por temas de políticas del banco', indica acercarse a una agencia y el código.",
    "ERROR": "Es una falla técnica temporal: NO uses la frase de políticas; pide reintentar e incluye el código.",
    "AWAITING_CUSTOMER": "Pide la información adicional.",
}


class CustomerMessageSchema(Schema):
    message = fields.String(required=True, validate=validate.Length(min=40, max=1200))


def guardrail_violations(message: str, code: str, document_id: str) -> list[str]:
    text = normalize(message)
    issues = [f"término prohibido '{t}'" for t in FORBIDDEN if t in text]
    if document_id in message or re.search(r"\d{10}", message):
        issues.append("cédula completa")
    if len(message.split()) > MAX_WORDS:
        issues.append(f"más de {MAX_WORDS} palabras")
    if not code.startswith("ONB-OK") and outcome(code).status != "AWAITING_CUSTOMER" and code not in message:
        issues.append("falta código de referencia")
    if outcome(code).status in ("REJECTED", "ESCALATED", "ERROR") and "1800" not in message:
        issues.append("faltan canales de ayuda")
    if outcome(code).status == "ERROR" and "por temas de politicas" in text:
        issues.append("frase de políticas en una falla técnica")
    return issues


def build_facts(state: dict) -> dict:
    request, decision = state["request"], state["decision"]
    product = repository.get_product(request["product"])
    approved = decision["status"].startswith("APPROVED")
    documents = [d["name"] for d in (state.get("documentation") or {}).get("required_documents", [])] if approved else []
    return {
        "first_name": first_name(request["prospect_name"]),
        "product_name": product["name"],
        "last4": request["document_id"][-4:],
        "documents": ", ".join(documents) if documents else ("los indicados en la app" if approved else ""),
        "status": decision["status"],
        "reason_code": decision["code"],
        # la solución propuesta es interna en aprobaciones (p.ej. monitoreo reforzado): no se comparte
        "next_step": None if approved else decision["proposed_solution"],
        "user_created": bool(state.get("provisioning") and state["provisioning"].get("status") == "created"),
    }


def response_agent_node(state: dict) -> dict:
    started = now()
    decision = state["decision"]
    code = decision["code"]
    rule = outcome(code)
    facts = build_facts(state)
    template = rule.template.format(**facts)
    mode, issues, llm_error, citations = "plantilla", [], None, []
    message = template

    if rule.llm_allowed and settings.openai_api_key:
        gate = ToolGate(AGENT, state["onboarding_id"], {
            "document_id": state["request"]["document_id"],
            "policy_scope": [rule.policy_ref.split()[0], "POL-COM-005"]})
        policy = gate.execute_for_llm("search_policies", {"query": f"Cómo comunicar al cliente: {rule.proposed_solution}"})
        citations = [r["section"] for r in policy.get("results", [])]
        examples = repository.response_examples(code)
        prompt = (
            f"Hechos del caso (únicos datos que puedes usar):\n{json.dumps(facts, ensure_ascii=False)}\n\n"
            f"Fragmentos de política aplicables:\n{json.dumps(policy.get('results', []), ensure_ascii=False)}\n\n"
            "Ejemplos de mensajes ideales:\n" + "\n".join(f"- {e['ideal_message']}" for e in examples) + "\n\n"
            f"Instrucción del caso: {CASE_GUIDANCE[outcome(code).status]}\n\n"
            f"Mensaje base aprobado por cumplimiento (mejora la redacción y personalízalo sin cambiar hechos, "
            f"códigos ni pasos):\n{template}\n\nEscribe solo el mensaje final para el cliente.")
        try:
            agent = repository.get_agent(AGENT)
            reply = chat_model(float(agent["temperature"])).invoke(
                [SystemMessage(agent["system_prompt"]), HumanMessage(prompt)])
            candidate = CustomerMessageSchema().load({"message": (reply.content or "").strip()})["message"]
            issues = guardrail_violations(candidate, code, state["request"]["document_id"])
            if not issues:
                message, mode = candidate, "llm"
        except ValidationError as exc:
            issues = [f"contrato: {exc.messages}"]
        except Exception as exc:  # noqa: BLE001
            llm_error = f"{type(exc).__name__}: {exc}"[:300]

    summary = {"llm": "Mensaje redactado por LLM (pasó guardrails POL-COM-005)",
               "plantilla": "Mensaje de plantilla aprobada"}[mode]
    if not rule.llm_allowed:
        summary += " (caso sensible: el LLM no redacta)"
    elif issues:
        summary += f" (guardrail rechazó al LLM: {'; '.join(issues)})"
    elif llm_error:
        summary += " (LLM no disponible)"
    trace = record_step(state, AGENT, AGENT, "ok", summary, started,
                        {"mode": mode, "guardrail_issues": issues, "llm_error": llm_error, "policy_sections": citations})
    return {"customer_message": message, "trace": [trace]}
