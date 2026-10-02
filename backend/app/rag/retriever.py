"""Recuperación: similitud coseno sobre pgvector con índice IVFFLAT (probes ajustado por sesión)."""
import time

from psycopg.types.json import Jsonb

from app.config import settings
from app.db.pool import connection
from app.rag.embeddings import embed_text


def search_policies(query: str, *, top_k: int | None = None, policy_codes: list[str] | None = None,
                    min_score: float | None = None, probes: int | None = None, exact: bool = False,
                    onboarding_id: str | None = None, agent_code: str = "system") -> list[dict]:
    top_k = top_k or settings.rag_top_k
    min_score = settings.rag_min_score if min_score is None else min_score
    probes = probes or settings.ivfflat_probes
    vector = embed_text(query)
    started = time.perf_counter()

    with connection() as conn, conn.transaction():
        if exact:
            conn.execute("SET LOCAL enable_indexscan = off")
        else:
            conn.execute(f"SET LOCAL ivfflat.probes = {int(probes)}")
            # pgvector >= 0.8: si hay filtro, sigue escaneando listas hasta completar top_k
            conn.execute("SET LOCAL ivfflat.iterative_scan = relaxed_order")
        rows = conn.execute(
            """SELECT c.id AS chunk_id, d.code AS policy_code, d.title, c.section_path, c.content,
                      1 - (c.embedding <=> %(v)s) AS score
               FROM rag.policy_chunk c JOIN rag.source_document d ON d.id = c.document_id
               WHERE (%(codes)s::text[] IS NULL OR d.code = ANY(%(codes)s::text[]))
               ORDER BY c.embedding <=> %(v)s
               LIMIT %(k)s""",
            {"v": vector, "codes": policy_codes, "k": top_k},
        ).fetchall()
    latency = int((time.perf_counter() - started) * 1000)
    results = [dict(r, score=round(float(r["score"]), 4)) for r in rows if r["score"] >= min_score]

    if onboarding_id or agent_code != "system":
        with connection() as conn:
            conn.execute(
                """INSERT INTO rag.retrieval_log (onboarding_id, agent_code, query_text, top_k, probes, results, latency_ms)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (onboarding_id, agent_code, query, top_k, None if exact else probes,
                 Jsonb([{"chunk_id": r["chunk_id"], "score": r["score"]} for r in results]), latency),
            )
    return results
