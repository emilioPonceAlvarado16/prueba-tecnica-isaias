"""Requiere la BD local levantada (manage_env.sh start db)."""
import uuid

from app.agents.tool_gate import ToolGate
from app.db import repository
from app.db.pool import execute, fetch_all


def _onboarding(document_id: str) -> str:
    onboarding_id = str(uuid.uuid4())
    repository.create_onboarding(onboarding_id, {"prospect_name": "Test", "document_id": document_id,
                                                 "product": "deposito_plazo"})
    return onboarding_id


def test_agente_no_puede_usar_tool_fuera_de_allowlist():
    onboarding_id = _onboarding("1715556666")
    try:
        gate = ToolGate("risk_agent", onboarding_id, {"document_id": "1715556666", "risk_name": "Lorena Espinosa"})
        response = gate.execute_for_llm("verify_identity", {})
        assert "no está permitida" in response["error"]
        assert gate.denied == ["verify_identity"]
        log = fetch_all("SELECT tool_code, status FROM core.tool_call_log WHERE onboarding_id = %s", (onboarding_id,))
        assert log == [{"tool_code": "verify_identity", "status": "denied"}]
    finally:
        execute("DELETE FROM core.onboarding_request WHERE id = %s", (onboarding_id,))


def test_reintentos_y_falla_critica_registrados():
    onboarding_id = _onboarding("0603344557")
    try:
        gate = ToolGate("identity_agent", onboarding_id, {"document_id": "0603344557"})
        assert gate.run("verify_identity", {}) is None
        assert gate.failures == {"verify_identity": "ONB-IDV-503"}
        log = fetch_all("SELECT status, attempt, args_masked->>'document_id' AS doc FROM core.tool_call_log "
                        "WHERE onboarding_id = %s ORDER BY attempt", (onboarding_id,))
        assert [r["attempt"] for r in log] == [1, 2, 3]                 # 1 intento + 2 reintentos (core.tool)
        assert {r["status"] for r in log} == {"timeout"}
        assert log[0]["doc"] == "060334****"                            # cédula enmascarada en auditoría
    finally:
        execute("DELETE FROM core.onboarding_request WHERE id = %s", (onboarding_id,))


def test_pii_no_llega_al_llm():
    onboarding_id = _onboarding("1004455661")
    try:
        gate = ToolGate("identity_agent", onboarding_id, {"document_id": "1004455661"})
        projected = gate.execute_for_llm("verify_identity", {"document_id": "9999999999"})  # el LLM no puede cambiarla
        assert set(projected) == {"verified", "confidence", "condicion"}
        assert gate.results["verify_identity"]["registry"]["nombres"] == "Gabriela"
    finally:
        execute("DELETE FROM core.onboarding_request WHERE id = %s", (onboarding_id,))
