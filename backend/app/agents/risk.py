"""Agente de Listas de Riesgo (POL-PLA-002). Tool permitido: check_risk_lists."""
from app.agents.base import agent_output, run_agent
from app.agents.tool_gate import ToolGate
from app.domain.cedula import mask
from app.domain.rules import risk_outcome
from app.graph.tracing import now, record_step

AGENT = "risk_agent"
TASK = "Consultar las listas de control de lavado de activos y sanciones para el prospecto y reportar el nivel de riesgo."


def risk_agent_node(state: dict) -> dict:
    started = now()
    request = state["request"]
    # Se consulta con el nombre oficial del Registro Civil (más completo que el declarado)
    name = state.get("identity", {}).get("registered_name") or request["prospect_name"]
    gate = ToolGate(AGENT, state["onboarding_id"], {"document_id": request["document_id"], "risk_name": name})
    run = run_agent(AGENT, TASK, {"cedula": mask(request["document_id"])}, gate, mandatory={"check_risk_lists": {}})

    if "check_risk_lists" in gate.failures:
        risk = {"tool_error": gate.failures["check_risk_lists"], "risk_level": None, "matches": [], "is_pep": False}
        summary = "Servicio de listas de control no respondió: no se puede aprobar (falla segura)."
    else:
        result = gate.results["check_risk_lists"]
        risk = {"risk_level": result["risk_level"], "matches": result["matches"],
                "is_pep": any(m["list_code"] == "PEP_EC" for m in result["matches"])}
        summary = f"Nivel de riesgo {risk['risk_level']}, {len(risk['matches'])} coincidencia(s)" + (
            f" [{', '.join(sorted({m['list_code'] for m in risk['matches']}))}]" if risk["matches"] else "")

    code = risk_outcome(risk)
    if code:
        summary += f" → {code}"
    status = {None: "ok", "ONB-RSK-002": "escalated", "ONB-RSK-001": "escalated"}.get(code, "failed")
    trace = record_step(state, AGENT, AGENT, status, summary, started, {"risk": risk, **agent_output(gate, run)})
    return {"risk": risk, "outcome_code": code, "trace": [trace]}
