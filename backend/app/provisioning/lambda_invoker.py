import json

import boto3

from app.config import settings
from app.db import repository

_client = None


def provision(onboarding_id: str, document_id: str, full_name: str, product: str, email: str | None) -> dict:
    global _client
    _client = _client or boto3.client("lambda")
    response = _client.invoke(
        FunctionName=settings.provisioner_lambda_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"onboarding_id": onboarding_id, "username": document_id, "name": full_name,
                            "product": product, "email": email}).encode(),
    )
    body = json.loads(response["Payload"].read() or "{}")
    if response.get("FunctionError") or body.get("status") not in ("created", "exists"):
        raise RuntimeError(body.get("error") or body.get("errorMessage") or "Lambda de provisión falló")
    if body["status"] == "created":
        repository.save_provisioned_user(onboarding_id, document_id, body["username"], "cognito", body.get("sub"),
                                         "created", None)
    return {"username": body["username"], "provider": "cognito", "status": "created",
            "temporary_password": body.get("temporary_password"), "existing": body["status"] == "exists"}
