"""Tool 1 (mock sobre BD real): verificación con el Registro Civil (ext.registro_civil)."""
from app.db.pool import fetch_one
from app.tools.faults import raise_if_faulty


def verify_identity(document_id: str) -> dict:
    raise_if_faulty("verify_identity", document_id)
    row = fetch_one("""SELECT nombres, apellidos, fecha_nacimiento, condicion, calidad_dato
                       FROM ext.registro_civil WHERE document_id = %s""", (document_id,))
    if row is None:
        return {"verified": False, "confidence": 0.0, "registry": None}
    return {
        "verified": row["condicion"] == "CIUDADANO",
        "confidence": float(row["calidad_dato"]),     # confianza que devolvería el proveedor biométrico
        "registry": {
            "nombres": row["nombres"],
            "apellidos": row["apellidos"],
            "fecha_nacimiento": row["fecha_nacimiento"],
            "condicion": row["condicion"],
        },
    }
