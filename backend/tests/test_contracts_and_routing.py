import pytest
from marshmallow import ValidationError

from app.contracts.onboarding import CustomerInfoSchema, OnboardingStartSchema
from app.graph.builder import route_after_decision, route_after_identity, route_after_risk, route_after_validation


def test_start_schema_ok():
    data = OnboardingStartSchema().load({"prospect_name": "Juan Perez", "document_id": "1712345675",
                                         "product": "cuenta_ahorros"})
    assert data["email"] is None


def test_start_schema_errors():
    with pytest.raises(ValidationError) as exc:
        OnboardingStartSchema().load({"prospect_name": "J1", "document_id": "17", "product": "tarjeta_oro"})
    assert set(exc.value.messages) == {"prospect_name", "document_id", "product"}


def test_customer_info_schema():
    with pytest.raises(ValidationError):
        CustomerInfoSchema().load({"actividad_economica": "Empleado", "origen_fondos": "Sueldo", "ingresos_mensuales": 0})


def test_routing():
    assert route_after_validation({"cedula_valid": False}) == "decision"
    assert route_after_validation({"cedula_valid": True}) == "identity_agent"
    assert route_after_identity({"outcome_code": "ONB-IDV-002"}) == "decision"
    assert route_after_identity({"outcome_code": None}) == "risk_agent"
    assert route_after_risk({"outcome_code": "ONB-RSK-002"}) == "request_customer_info"
    assert route_after_risk({"outcome_code": "ONB-RSK-001"}) == "decision"
    assert route_after_risk({"outcome_code": None}) == "policy_agent"
    assert route_after_decision({"decision": {"status": "APPROVED"}}) == "provision_user"
    assert route_after_decision({"decision": {"status": "ESCALATED"}}) == "response_agent"
