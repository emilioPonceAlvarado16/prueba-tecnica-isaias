"""Adaptador API Gateway (HTTP API, payload v2) -> Flask, para la Lambda 'onboarding-api'."""
from apig_wsgi import make_lambda_handler

from app.main import app

handler = make_lambda_handler(app)
