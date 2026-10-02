"""Tool de RAG: búsqueda semántica en políticas (pgvector + IVFFLAT)."""
from app.rag.retriever import search_policies as _search


def search_policies(query: str, policy_code: str | None = None, *, onboarding_id: str | None = None,
                    agent_code: str = "system", policy_codes: list[str] | None = None) -> dict:
    codes = [policy_code] if policy_code else policy_codes
    hits = _search(query, policy_codes=codes, onboarding_id=onboarding_id, agent_code=agent_code)
    return {"results": [{k: h[k] for k in ("chunk_id", "policy_code", "section_path", "content", "score")} for h in hits]}
