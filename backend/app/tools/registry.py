"""Registro de tools: función, contratos marshmallow, inyección de datos desde el estado y proyección al LLM.

Los datos personales (cédula, nombre) NUNCA vienen del LLM: se inyectan desde el contexto del grafo.
Lo que el LLM ve de cada resultado es una proyección sin PII.
"""
from dataclasses import dataclass
from typing import Callable

from marshmallow import Schema

from app.contracts import tools as c
from app.tools.check_risk_lists import check_risk_lists
from app.tools.prepare_documentation import prepare_documentation
from app.tools.search_policies import search_policies
from app.tools.verify_identity import verify_identity


@dataclass(frozen=True)
class ToolSpec:
    fn: Callable[..., dict]
    input_schema: Schema
    output_schema: Schema
    build_args: Callable[[dict, dict], tuple[dict, dict]]   # (contexto, args_llm) -> (args, kwargs)
    for_llm: Callable[[dict], dict]


def _search_args(ctx: dict, llm: dict) -> tuple[dict, dict]:
    code = llm.get("policy_code")
    scope = ctx.get("policy_scope")
    if scope and code not in scope:
        code = None
    return ({"query": llm.get("query") or ctx.get("default_query", "requisitos"), "policy_code": code},
            {"onboarding_id": ctx["onboarding_id"], "agent_code": ctx["agent_code"], "policy_codes": scope})


TOOLS: dict[str, ToolSpec] = {
    "verify_identity": ToolSpec(
        fn=verify_identity,
        input_schema=c.VerifyIdentityInput(),
        output_schema=c.VerifyIdentityOutput(),
        build_args=lambda ctx, llm: ({"document_id": ctx["document_id"]}, {}),
        for_llm=lambda r: {"verified": r["verified"], "confidence": r["confidence"],
                           "condicion": (r.get("registry") or {}).get("condicion", "NO_REGISTRADO")},
    ),
    "check_risk_lists": ToolSpec(
        fn=check_risk_lists,
        input_schema=c.CheckRiskListsInput(),
        output_schema=c.CheckRiskListsOutput(),
        build_args=lambda ctx, llm: ({"name": ctx["risk_name"], "document_id": ctx["document_id"]}, {}),
        for_llm=lambda r: {"risk_level": r["risk_level"], "matches": len(r["matches"]),
                           "match_types": sorted({m["match_type"] for m in r["matches"]})},
    ),
    "prepare_documentation": ToolSpec(
        fn=prepare_documentation,
        input_schema=c.PrepareDocumentationInput(),
        output_schema=c.PrepareDocumentationOutput(),
        # el producto se toma del estado aunque el LLM proponga otro (no puede cambiar la solicitud)
        build_args=lambda ctx, llm: ({"product": ctx["product"], "client_data": ctx["client_data"]},
                                     {"document_id": ctx["document_id"]}),
        for_llm=lambda r: {"product": r["product"], "documents": [d["name"] for d in r["required_documents"]]},
    ),
    "search_policies": ToolSpec(
        fn=search_policies,
        input_schema=c.SearchPoliciesInput(),
        output_schema=c.SearchPoliciesOutput(),
        build_args=_search_args,
        for_llm=lambda r: {"results": [{"policy": h["policy_code"], "section": h["section_path"],
                                        "text": h["content"][:700], "score": h["score"]} for h in r["results"]]},
    ),
}
