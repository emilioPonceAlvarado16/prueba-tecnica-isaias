"""Tool 3 (mock sobre BD real): documentos requeridos (core.product_document_requirement) - POL-PRD-003."""
from app.db.pool import fetch_all
from app.tools.faults import raise_if_faulty


def prepare_documentation(product: str, client_data: dict, *, document_id: str = "") -> dict:
    raise_if_faulty("prepare_documentation", document_id)
    conditions = ["always"]
    if client_data["risk_level"] in ("medium", "high"):
        conditions.append("risk_medium")
    if client_data["is_pep"]:
        conditions.append("pep")
    rows = fetch_all(
        """SELECT DISTINCT ON (d.code) d.code, d.name, r.mandatory, r.policy_ref
           FROM core.product_document_requirement r JOIN core.document_type d ON d.code = r.document_code
           WHERE r.product_code = %s AND r.condition = ANY(%s)
           ORDER BY d.code, r.condition""",
        (product, conditions),
    )
    order = {"CEDULA": 0, "PLANILLA_SERVICIO": 1, "FORMULARIO_KYC": 2, "TERMINOS_CONDICIONES": 3}
    docs = sorted(rows, key=lambda r: (order.get(r["code"], 9), r["code"]))
    return {"product": product, "required_documents": [dict(r, source="catalog") for r in docs]}
