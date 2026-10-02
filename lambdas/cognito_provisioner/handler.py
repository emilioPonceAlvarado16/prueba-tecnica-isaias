"""Lambda 'cognito-provisioner': crea el usuario de banca digital en Cognito cuando el onboarding es exitoso.

Evento:  {"onboarding_id", "username" (cédula), "name", "product", "email"?}
Retorno: {"status": "created"|"exists"|"failed", "username", "sub", "temporary_password"?, "error"?}
"""
import os
import secrets
import string

import boto3

cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ["USER_POOL_ID"]
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"


def temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Ad" + "".join(secrets.choice(alphabet) for _ in range(9)) + "7!"


def handler(event, context):
    username = event["username"]
    try:
        try:
            user = cognito.admin_get_user(UserPoolId=USER_POOL_ID, Username=username)
            sub = next(a["Value"] for a in user["UserAttributes"] if a["Name"] == "sub")
            return {"status": "exists", "username": username, "sub": sub}
        except cognito.exceptions.UserNotFoundException:
            pass

        password = temporary_password()
        attributes = [{"Name": "name", "Value": event["name"]},
                      {"Name": "custom:product", "Value": event["product"]},
                      {"Name": "custom:onboarding_id", "Value": event["onboarding_id"]}]
        kwargs = {"UserPoolId": USER_POOL_ID, "Username": username, "TemporaryPassword": password,
                  "UserAttributes": attributes}
        if event.get("email"):
            attributes += [{"Name": "email", "Value": event["email"]}, {"Name": "email_verified", "Value": "true"}]
            kwargs["DesiredDeliveryMediums"] = ["EMAIL"]          # Cognito envía la invitación con la clave temporal
        else:
            kwargs["MessageAction"] = "SUPPRESS"

        created = cognito.admin_create_user(**kwargs)
        sub = next(a["Value"] for a in created["User"]["Attributes"] if a["Name"] == "sub")
        return {"status": "created", "username": username, "sub": sub,
                "temporary_password": password if DEMO_MODE else None}
    except Exception as exc:  # noqa: BLE001 - el backend traduce cualquier falla a ONB-PRV-503
        return {"status": "failed", "username": username, "error": f"{type(exc).__name__}: {exc}"[:300]}
