"""Reglas de decisión determinísticas (sección 4 de la propuesta).

Los LLM interpretan y redactan; los umbrales de aptitud se evalúan aquí, sobre la salida cruda de los tools.
Cada regla devuelve un código de app.domain.error_codes o None si el flujo puede continuar.
"""
from datetime import date

from app.config import settings


def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def identity_outcome(identity: dict, min_age: int) -> str | None:
    """identity: salida normalizada del identity_agent."""
    if identity.get("tool_error"):
        return "ONB-IDV-503"
    if not identity["verified"]:
        return "ONB-IDV-001"
    if identity["confidence"] < settings.min_identity_confidence:
        return "ONB-IDV-002"
    if identity["name_match"] < settings.min_name_match:
        return "ONB-IDV-003"
    if identity["age"] is not None and identity["age"] < min_age:
        return "ONB-IDV-004"
    return None


def risk_outcome(risk: dict) -> str | None:
    if risk.get("tool_error"):
        return "ONB-RSK-503"
    if risk["risk_level"] == "high":
        return "ONB-RSK-001"
    if risk["risk_level"] == "medium":
        return "ONB-RSK-002"
    return None
