from app.db import repository
from app.provisioning import temporary_password


def provision(onboarding_id: str, document_id: str, full_name: str, product: str, email: str | None) -> dict:
    existing = repository.get_provisioned_by_document(document_id)
    if existing:
        return {"username": existing["username"], "provider": "local_mock", "status": "created",
                "temporary_password": None, "existing": True}
    password = temporary_password()
    repository.save_provisioned_user(onboarding_id, document_id, document_id, "local_mock", None, "created", None)
    return {"username": document_id, "provider": "local_mock", "status": "created", "temporary_password": password}
