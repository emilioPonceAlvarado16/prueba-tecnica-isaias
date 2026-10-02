import logging

from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from werkzeug.exceptions import HTTPException

from app.api.onboarding import blp
from app.config import settings


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        API_TITLE="Onboarding Digital Multi-Agente - Banco Andino Demo",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/api/v1",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
        JSON_SORT_KEYS=False,
    )
    app.json.ensure_ascii = False
    CORS(app, origins=list(settings.cors_origins))
    api = Api(app)
    api.register_blueprint(blp)

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        data = getattr(exc, "data", {}) or {}
        if exc.code == 400 and "messages" in data:          # validación marshmallow
            errors = {}
            for location in data["messages"].values():
                for field, msgs in location.items():
                    errors[field] = msgs if isinstance(msgs, list) else [str(msgs)]
            return jsonify(code="ONB-VAL-400", message="La solicitud tiene datos inválidos.", errors=errors), 400
        message = (data.get("message") if isinstance(data, dict) else None) or exc.description
        return jsonify(code=f"HTTP-{exc.code}", message=message), exc.code

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.api_port, debug=False, threaded=True)
