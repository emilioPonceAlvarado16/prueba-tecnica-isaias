"""RAG de tools: dado el objetivo de un agente, recupera los tools semánticamente relevantes.

Scan exacto (sin índice ANN): con pocas filas es más rápido y con recall 100%.
La seguridad NO depende de esto: el resultado siempre se intersecta con core.agent_tool_permission.
"""
from functools import lru_cache

from app.db.pool import fetch_all
from app.rag.embeddings import embed_text


@lru_cache(maxsize=64)
def retrieve_tools(task: str, top_k: int = 3) -> tuple[tuple[str, float], ...]:
    rows = fetch_all(
        """SELECT tool_code, 1 - (embedding <=> %s) AS score FROM rag.tool_embedding
           ORDER BY embedding <=> %s LIMIT %s""",
        (embed_text(task), embed_text(task), top_k),
    )
    return tuple((r["tool_code"], round(float(r["score"]), 4)) for r in rows)
