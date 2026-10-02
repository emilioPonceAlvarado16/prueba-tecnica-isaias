"""Tool 2 (mock sobre BD real): listas de control (ext.risk_list_entry) - POL-PLA-002 Art. 3 y 4."""
from app.db.pool import fetch_all
from app.tools.faults import raise_if_faulty

NAME_SIMILARITY = 0.85
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def check_risk_lists(name: str, document_id: str) -> dict:
    raise_if_faulty("check_risk_lists", document_id)
    rows = fetch_all(
        """SELECT e.list_code, l.severity::text AS severity,
                  CASE WHEN e.document_id = %(doc)s THEN 'document' ELSE 'name' END AS match_type,
                  GREATEST(similarity(core.normalize_name(e.full_name), core.normalize_name(%(name)s)),
                           COALESCE((SELECT max(similarity(core.normalize_name(a), core.normalize_name(%(name)s)))
                                     FROM unnest(e.aliases) a), 0)) AS score
           FROM ext.risk_list_entry e JOIN ext.risk_list l ON l.code = e.list_code
           WHERE e.active AND (
                 e.document_id = %(doc)s
              OR similarity(core.normalize_name(e.full_name), core.normalize_name(%(name)s)) >= %(th)s
              OR EXISTS (SELECT 1 FROM unnest(e.aliases) a
                         WHERE similarity(core.normalize_name(a), core.normalize_name(%(name)s)) >= %(th)s))""",
        {"doc": document_id, "name": name, "th": NAME_SIMILARITY},
    )
    matches = [{"list_code": r["list_code"], "severity": r["severity"], "match_type": r["match_type"],
                "score": 1.0 if r["match_type"] == "document" else round(float(r["score"]), 3)} for r in rows]
    level = max((m["severity"] for m in matches), key=SEVERITY_ORDER.get, default="low")
    return {"risk_level": level, "matches": matches}
