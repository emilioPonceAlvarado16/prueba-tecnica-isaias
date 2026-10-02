"""Contratos marshmallow de la API de onboarding."""
from marshmallow import Schema, ValidationError, fields, validate, validates

from app.db import repository

NAME_REGEX = r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü' ]+$"

STATUSES = ["RECEIVED", "IN_PROGRESS", "AWAITING_CUSTOMER", "APPROVED", "APPROVED_PENDING_PROVISIONING",
            "REJECTED", "ESCALATED", "ERROR"]
NEXT_ACTIONS = ["LOGIN", "VISIT_BRANCH", "PROVIDE_INFO", "RETRY_LATER", "FIX_INPUT", "NONE"]


class OnboardingStartSchema(Schema):
    prospect_name = fields.String(required=True, validate=[
        validate.Length(min=3, max=160),
        validate.Regexp(NAME_REGEX, error="Solo se permiten letras y espacios."),
    ])
    document_id = fields.String(required=True, validate=validate.Regexp(
        r"^\d{10}$", error="La cédula debe tener exactamente 10 dígitos."))
    product = fields.String(required=True)
    email = fields.Email(required=False, allow_none=True, load_default=None)

    @validates("product")
    def validate_product(self, value: str, **_):
        if value not in repository.active_product_codes():
            raise ValidationError(f"Producto no disponible para apertura digital: {value}.")


class CustomerInfoSchema(Schema):
    """Debida diligencia reforzada (POL-PLA-002 Art. 6)."""
    actividad_economica = fields.String(required=True, validate=validate.Length(min=3, max=120))
    origen_fondos = fields.String(required=True, validate=validate.Length(min=3, max=120))
    ingresos_mensuales = fields.Float(required=True, validate=validate.Range(min=1, max=1_000_000))


class OnboardingContinueSchema(Schema):
    answers = fields.Nested(CustomerInfoSchema, required=True)


class NextActionSchema(Schema):
    type = fields.String(required=True, validate=validate.OneOf(NEXT_ACTIONS))
    detail = fields.String(allow_none=True)


class RequiredDocumentSchema(Schema):
    code = fields.String(required=True)
    name = fields.String(required=True)
    mandatory = fields.Boolean(required=True)
    policy_ref = fields.String(allow_none=True)
    source = fields.String(load_default="catalog")


class PendingQuestionSchema(Schema):
    field = fields.String(required=True)
    label = fields.String(required=True)
    type = fields.String(required=True, validate=validate.OneOf(["text", "number", "select"]))
    options = fields.List(fields.String(), allow_none=True)
    required = fields.Boolean(required=True)


class AgentTraceSchema(Schema):
    node = fields.String(required=True)
    agent = fields.String(allow_none=True)
    status = fields.String(required=True)
    summary = fields.String(allow_none=True)
    started_at = fields.DateTime(required=True)
    duration_ms = fields.Integer(allow_none=True)


class ProvisioningSchema(Schema):
    username = fields.String(required=True)
    provider = fields.String(required=True)
    status = fields.String(required=True)
    temporary_password = fields.String(allow_none=True)


class ErrorSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)


class MessageSchema(Schema):
    role = fields.String(required=True)
    content = fields.String(required=True)
    created_at = fields.DateTime(required=True)


class OnboardingResultSchema(Schema):
    onboarding_id = fields.UUID(required=True)
    status = fields.String(required=True, validate=validate.OneOf(STATUSES))
    reason_code = fields.String(allow_none=True)
    customer_message = fields.String(allow_none=True)
    proposed_solution = fields.String(allow_none=True)
    next_action = fields.Nested(NextActionSchema, required=True)
    required_documents = fields.List(fields.Nested(RequiredDocumentSchema), required=True)
    pending_questions = fields.List(fields.Nested(PendingQuestionSchema), required=True)
    agents_trace = fields.List(fields.Nested(AgentTraceSchema), required=True)
    provisioning = fields.Nested(ProvisioningSchema, allow_none=True)
    error = fields.Nested(ErrorSchema, allow_none=True)
    prospect_name = fields.String()
    document_id_masked = fields.String()
    product = fields.String()
    created_at = fields.DateTime(required=True)
    messages = fields.List(fields.Nested(MessageSchema))


class ApiErrorSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)
    errors = fields.Dict(keys=fields.String(), values=fields.List(fields.String()))
    onboarding_id = fields.UUID(allow_none=True)


class ProductSchema(Schema):
    code = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
