"""Provisión del usuario de banca digital tras la aprobación.

PROVISIONER=local  -> core.provisioned_user (mock local, sin AWS)
PROVISIONER=lambda -> invoca la Lambda 'cognito-provisioner' (AdminCreateUser en Cognito)
"""
import secrets
import string

from app.config import settings


def temporary_password() -> str:
    """Cumple la política por defecto de Cognito: mayúscula, minúscula, número, símbolo, >= 8."""
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(9))
    return f"Ad{core}7!"


def provision(onboarding_id: str, document_id: str, full_name: str, product: str, email: str | None) -> dict:
    if settings.provisioner == "lambda":
        from app.provisioning.lambda_invoker import provision as impl
    else:
        from app.provisioning.local_mock import provision as impl
    return impl(onboarding_id, document_id, full_name, product, email)
