"""Estado del orquestador. Se persiste en PostgreSQL (esquema checkpoint) por thread_id = onboarding_id."""
import operator
from typing import Annotated, TypedDict


class OnboardingRequest(TypedDict):
    prospect_name: str
    document_id: str
    product: str
    email: str | None


class OnboardingState(TypedDict, total=False):
    onboarding_id: str
    request: OnboardingRequest
    cedula_valid: bool
    identity: dict            # verified, confidence, condicion, registered_name, name_match, age, tool_error
    risk: dict                # risk_level, matches, is_pep, tool_error
    outcome_code: str | None  # primera regla que dispara (domain/error_codes.py); None = puede continuar
    edd: bool                 # se aplicó debida diligencia reforzada (riesgo medio con info del cliente)
    customer_inputs: dict
    documentation: dict       # required_documents, citations, source
    decision: dict            # code, status, next_action, queue, proposed_solution, policy_ref
    provisioning: dict | None
    customer_message: str
    trace: Annotated[list[dict], operator.add]
