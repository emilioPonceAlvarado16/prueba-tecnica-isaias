"""Agente de Identidad (POL-KYC-001). Tool permitido: verify_identity."""
from datetime import date

from app.agents.base import agent_output, run_agent
from app.agents.tool_gate import ToolGate
from app.db import repository
from app.domain.cedula import mask
from app.domain.error_codes import outcome
from app.domain.names import name_match_score
from app.domain.rules import age_on, identity_outcome
from app.graph.tracing import now, record_step

AGENT = "identity_agent"
TASK = "Verificar la identidad del prospecto contra el Registro Civil y reportar si está verificado y con qué confianza."


def identity_agent_node(state: dict) -> dict:
    started = now()
    request = state["request"]
    gate = ToolGate(AGENT, state["onboarding_id"], {"document_id": request["document_id"]})
    run = run_agent(AGENT, TASK, {"cedula": mask(request["document_id"]), "producto": request["product"]},
                    gate, mandatory={"verify_identity": {}})

    if "verify_identity" in gate.failures:
        identity = {"tool_error": gate.failures["verify_identity"], "verified": False, "confidence": 0.0,
                    "name_match": 0.0, "age": None, "condicion": None, "registered_name": None}
        summary = "Registro Civil no respondió tras los reintentos configurados."
    else:
        result = gate.results["verify_identity"]
        registry = result["registry"]
        registered_name = f"{registry['nombres']} {registry['apellidos']}" if registry else None
        identity = {
            "verified": result["verified"],
            "confidence": result["confidence"],
            "condicion": registry["condicion"] if registry else "NO_REGISTRADO",
            "registered_name": registered_name,
            "name_match": name_match_score(request["prospect_name"], registered_name) if registered_name else 0.0,
            "age": age_on(date.fromisoformat(str(registry["fecha_nacimiento"])), date.today()) if registry else None,
        }
        summary = (f"Registro Civil: {identity['condicion']}, verificado={identity['verified']}, "
                   f"confianza {identity['confidence']:.2f}, coincidencia de nombre {identity['name_match']:.2f}"
                   + (f", edad {identity['age']}" if identity["age"] is not None else ""))

    product = repository.get_product(request["product"])
    code = identity_outcome(identity, product["min_age"])
    if code:
        summary += f" → {code}"
    status = "ok" if code is None else ("failed" if outcome(code).status in ("REJECTED", "ERROR") else "escalated")
    trace = record_step(state, AGENT, AGENT, status, summary, started,
                        {"identity": {k: v for k, v in identity.items() if k != "registered_name"},
                         **agent_output(gate, run)})
    return {"identity": identity, "outcome_code": code, "trace": [trace]}
