from flask import jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.contracts.onboarding import (ApiErrorSchema, OnboardingContinueSchema, OnboardingResultSchema,
                                      OnboardingStartSchema, ProductSchema)
from app.db import repository
from app.services import onboarding as service

def _error(status: int, code: str, message: str, **extra):
    """Errores de negocio: Response directa (flask-smorest no la re-serializa con el schema 200)."""
    response = jsonify(ApiErrorSchema().dump({"code": code, "message": message, **extra}))
    response.status_code = status
    return response


blp = Blueprint("onboarding", __name__, url_prefix="/api/v1", description="Onboarding digital multi-agente")


@blp.route("/onboarding/start")
class OnboardingStart(MethodView):
    @blp.arguments(OnboardingStartSchema, error_status_code=400)
    @blp.response(200, OnboardingResultSchema)
    @blp.alt_response(400, schema=ApiErrorSchema, description="Validación de contrato")
    @blp.alt_response(409, schema=ApiErrorSchema, description="Solicitud duplicada")
    @blp.alt_response(503, schema=OnboardingResultSchema, description="Servicio crítico no disponible")
    def post(self, data):
        """Inicia el onboarding: ejecuta el grafo de agentes y devuelve el resultado."""
        try:
            result, status = service.start(data)
        except service.DuplicateOnboarding as exc:
            return _error(409, "ONB-DUP-409", "Ya tienes una solicitud registrada o aprobada para este producto. "
                                              "Puedes consultar su estado con el enlace de tu solicitud.",
                          onboarding_id=exc.onboarding_id)
        return result, status


@blp.route("/onboarding/<uuid:onboarding_id>")
class OnboardingDetail(MethodView):
    @blp.response(200, OnboardingResultSchema)
    def get(self, onboarding_id):
        """Estado, traza de agentes y conversación de un onboarding."""
        result = service.get_result(str(onboarding_id), include_messages=True)
        if result is None:
            abort(404, message="Onboarding no encontrado")
        return result


@blp.route("/onboarding/<uuid:onboarding_id>/continue")
class OnboardingContinue(MethodView):
    @blp.arguments(OnboardingContinueSchema, error_status_code=400)
    @blp.response(200, OnboardingResultSchema)
    def post(self, data, onboarding_id):
        """Reanuda un onboarding en AWAITING_CUSTOMER con la información del cliente."""
        try:
            result, status = service.resume(str(onboarding_id), data["answers"])
        except LookupError:
            abort(404, message="Onboarding no encontrado")
        except service.NotAwaitingCustomer as exc:
            return _error(409, "ONB-STA-409", f"La solicitud no está esperando información (estado {exc}).")
        result["messages"] = repository.get_messages(str(onboarding_id))
        return result, status


@blp.route("/products")
class Products(MethodView):
    @blp.response(200, ProductSchema(many=True))
    def get(self):
        """Productos disponibles para apertura digital."""
        return repository.list_products()


@blp.route("/health")
class Health(MethodView):
    def get(self):
        from app.config import settings
        from app.db.pool import fetch_one
        chunks = fetch_one("SELECT count(*) AS n FROM rag.policy_chunk")["n"]
        return {"status": "ok", "database": "ok", "rag_chunks": chunks,
                "openai_configured": bool(settings.openai_api_key), "provisioner": settings.provisioner}
