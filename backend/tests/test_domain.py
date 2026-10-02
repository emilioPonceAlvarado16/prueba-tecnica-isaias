from datetime import date

from app.domain.cedula import check_digit, mask, validate_cedula
from app.domain.names import name_match_score
from app.domain.rules import age_on, identity_outcome, risk_outcome


def test_cedula_valida():
    assert validate_cedula("1712345675").valid
    assert validate_cedula("0918765439").valid


def test_cedula_del_enunciado_es_invalida():
    result = validate_cedula("1712345678")
    assert not result.valid and "verificador" in result.reason
    assert check_digit("171234567") == 5


def test_cedula_provincia_y_tercer_digito():
    assert not validate_cedula("2512345678").valid
    assert not validate_cedula("1772345678").valid
    assert not validate_cedula("17123").valid


def test_mask():
    assert mask("1712345675") == "171234****"


def test_name_match():
    assert name_match_score("Juan Perez", "Juan Andrés Pérez Molina") == 1.0
    assert name_match_score("Pedro Gomez", "Ana Lucía Villacís Ruiz") < 0.6
    assert name_match_score("Maria Fernanda Loor", "María Fernanda Loor Zambrano") == 1.0


def test_age():
    assert age_on(date(2010, 1, 20), date(2026, 10, 2)) == 16
    assert age_on(date(1990, 10, 3), date(2026, 10, 2)) == 35


def base_identity(**kw):
    data = {"verified": True, "confidence": 0.95, "name_match": 1.0, "age": 30}
    data.update(kw)
    return data


def test_identity_rules_order():
    assert identity_outcome(base_identity(), 18) is None
    assert identity_outcome(base_identity(tool_error="x"), 18) == "ONB-IDV-503"
    assert identity_outcome(base_identity(verified=False), 18) == "ONB-IDV-001"
    assert identity_outcome(base_identity(confidence=0.79), 18) == "ONB-IDV-002"
    assert identity_outcome(base_identity(confidence=0.80), 18) is None
    assert identity_outcome(base_identity(name_match=0.3), 18) == "ONB-IDV-003"
    assert identity_outcome(base_identity(age=17), 18) == "ONB-IDV-004"


def test_risk_rules():
    assert risk_outcome({"risk_level": "low"}) is None
    assert risk_outcome({"risk_level": "medium"}) == "ONB-RSK-002"
    assert risk_outcome({"risk_level": "high"}) == "ONB-RSK-001"
    assert risk_outcome({"risk_level": "low", "tool_error": "x"}) == "ONB-RSK-503"
