"""Contratos marshmallow de entrada/salida de los tools (se validan en cada ejecución)."""
from marshmallow import Schema, fields, validate

RISK_LEVELS = ["low", "medium", "high"]


class RegistrySnapshotSchema(Schema):
    nombres = fields.String(required=True)
    apellidos = fields.String(required=True)
    fecha_nacimiento = fields.Date(required=True)
    condicion = fields.String(required=True)


class VerifyIdentityInput(Schema):
    document_id = fields.String(required=True, validate=validate.Regexp(r"^\d{10}$"))


class VerifyIdentityOutput(Schema):
    verified = fields.Boolean(required=True)
    confidence = fields.Float(required=True, validate=validate.Range(min=0, max=1))
    registry = fields.Nested(RegistrySnapshotSchema, allow_none=True)


class CheckRiskListsInput(Schema):
    name = fields.String(required=True, validate=validate.Length(min=2))
    document_id = fields.String(required=True, validate=validate.Regexp(r"^\d{10}$"))


class RiskMatchSchema(Schema):
    list_code = fields.String(required=True)
    severity = fields.String(required=True, validate=validate.OneOf(RISK_LEVELS))
    match_type = fields.String(required=True, validate=validate.OneOf(["document", "name"]))
    score = fields.Float(required=True)


class CheckRiskListsOutput(Schema):
    risk_level = fields.String(required=True, validate=validate.OneOf(RISK_LEVELS))
    matches = fields.List(fields.Nested(RiskMatchSchema), required=True)


class ClientDataSchema(Schema):
    risk_level = fields.String(required=True, validate=validate.OneOf(RISK_LEVELS))
    is_pep = fields.Boolean(required=True)


class PrepareDocumentationInput(Schema):
    product = fields.String(required=True)
    client_data = fields.Nested(ClientDataSchema, required=True)


class DocumentSchema(Schema):
    code = fields.String(required=True)
    name = fields.String(required=True)
    mandatory = fields.Boolean(required=True)
    policy_ref = fields.String(allow_none=True)
    source = fields.String(required=True)


class PrepareDocumentationOutput(Schema):
    product = fields.String(required=True)
    required_documents = fields.List(fields.Nested(DocumentSchema), required=True)


class SearchPoliciesInput(Schema):
    query = fields.String(required=True, validate=validate.Length(min=3))
    policy_code = fields.String(allow_none=True, load_default=None)


class PolicyHitSchema(Schema):
    chunk_id = fields.Integer(required=True)
    policy_code = fields.String(required=True)
    section_path = fields.String(required=True)
    content = fields.String(required=True)
    score = fields.Float(required=True)


class SearchPoliciesOutput(Schema):
    results = fields.List(fields.Nested(PolicyHitSchema), required=True)
