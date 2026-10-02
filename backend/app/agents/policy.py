"""Agente de Políticas. Tools permitidos: search_policies (RAG) y prepare_documentation.

Si prepare_documentation falla (tool no crítico), la documentación se deriva de la política POL-PRD-003
recuperada por RAG (fuente 'rag_fallback').
"""
import re
import unicodedata

from app.agents.base import agent_output, run_agent
from app.agents.tool_gate import ToolGate
from app.db import repository
from app.graph.tracing import now, record_step
from app.rag.retriever import search_policies

AGENT = "policy_agent"


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")[:40]


def documents_from_policy(state: dict, product_name: str, needs_edd: bool) -> list[dict]:
    """Fallback: lee la fila del producto en la tabla de POL-PRD-003 recuperada por RAG."""
    hits = search_policies(f"documentos requeridos {product_name}", policy_codes=["POL-PRD-003"], top_k=5,
                           onboarding_id=state["onboarding_id"], agent_code=AGENT)
    row = next((h for h in hits if h["section_path"].lower().endswith(product_name.lower())), None)
    if row is None:
        return []
    fields = dict(re.findall(r"([^.:]+): ([^.]+(?:\.\d[^.]*)*)\.", row["content"]))
    fields = {k.strip(): v.strip() for k, v in fields.items()}
    docs = []
    for key, mandatory in (("Documentos requeridos siempre", True),
                           ("Documentos adicionales con riesgo medio o PEP", True)):
        if key.startswith("Documentos adicionales") and not needs_edd:
            continue
        for name in fields.get(key, "").split(";"):
            if name.strip():
                docs.append({"code": _slug(name.strip()), "name": name.strip().capitalize(), "mandatory": mandatory,
                             "policy_ref": row["section_path"], "source": "rag_fallback"})
    return docs


def citation_label(section_path: str) -> str:
    """'POL-KYC-001 > Artículo 4. Nivel...' -> 'POL-KYC-001 Art. 4'; 'POL-PRD-003 > 2. Req... > Cuenta corriente' -> 'POL-PRD-003 §2 (Cuenta corriente)'."""
    parts = section_path.split(" > ")
    code, heading = parts[0], parts[1] if len(parts) > 1 else ""
    number = re.match(r"(?:Artículo |SECCIÓN )?(\d+)\.", heading)
    label = f"{code} {'Art. ' if heading.startswith('Artículo') else '§'}{number.group(1)}" if number else f"{code} {heading}"
    return label + (f" ({parts[2]})" if len(parts) > 2 else "")


def policy_agent_node(state: dict) -> dict:
    started = now()
    request = state["request"]
    product = repository.get_product(request["product"])
    risk = state.get("risk") or {}
    client_data = {"risk_level": risk.get("risk_level") or "low", "is_pep": bool(risk.get("is_pep"))}
    level_text = {"low": "bajo", "medium": "medio", "high": "alto"}[client_data["risk_level"]]
    default_query = f"requisitos y documentos para abrir {product['name']} con riesgo {level_text}"
    if client_data["is_pep"]:
        default_query += " persona expuesta políticamente"

    task = (f"Prepara la documentación para abrir una {product['name']} ({product['code']}) a un cliente con riesgo "
            f"{level_text}{' que es Persona Expuesta Políticamente' if client_data['is_pep'] else ''}. Busca en las "
            "políticas los requisitos aplicables y obtén la lista oficial de documentos requeridos.")
    gate = ToolGate(AGENT, state["onboarding_id"], {"document_id": request["document_id"], "product": product["code"],
                                                    "client_data": client_data, "default_query": default_query})
    run = run_agent(AGENT, task, {"producto": product["code"], **client_data,
                                  "info_adicional_cliente": bool(state.get("customer_inputs"))},
                    gate, mandatory={"search_policies": {"query": default_query},
                                     "prepare_documentation": {"product": product["code"]}})

    if "prepare_documentation" in gate.results:
        documents, source = gate.results["prepare_documentation"]["required_documents"], "catalog"
    else:
        documents = documents_from_policy(state, product["name"], client_data["risk_level"] != "low")
        source = "rag_fallback"

    hits = [h for result in gate.history.get("search_policies", []) for h in result["results"]]
    citations, seen = [], set()
    for hit in sorted(hits, key=lambda h: -h["score"]):
        if hit["section_path"] not in seen:
            seen.add(hit["section_path"])
            citations.append({"policy_code": hit["policy_code"], "section_path": hit["section_path"],
                              "label": citation_label(hit["section_path"]), "score": hit["score"]})
    citations = citations[:4]

    summary = (f"{len(documents)} documento(s) requeridos (fuente: "
               f"{'catálogo' if source == 'catalog' else 'políticas vía RAG, servicio de documentación caído'})"
               f" · políticas citadas: {', '.join(c['label'] for c in citations) or 'ninguna'}")
    status = "ok" if documents else "failed"
    documentation = {"required_documents": documents, "citations": citations, "source": source}
    trace = record_step(state, AGENT, AGENT, status, summary, started,
                        {"documentation": documentation, **agent_output(gate, run)})
    return {"documentation": documentation, "trace": [trace]}
