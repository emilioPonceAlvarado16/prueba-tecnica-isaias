"""Pipeline RAG: ingesta -> chunking híbrido -> embeddings -> pgvector -> índice IVFFLAT.

Uso:
    uv run python -m app.rag.ingest            # ingesta idempotente (omite documentos con el mismo sha256)
    uv run python -m app.rag.ingest --force    # re-ingesta todo
"""
import argparse
import math
import time

from psycopg.types.json import Jsonb

from app.config import settings
from app.db.pool import connection, fetch_all
from app.rag.chunking import hybrid_chunks
from app.rag.embeddings import embed_texts
from app.rag.loaders import LoadedDocument, load_all
from app.tools.catalog import TOOL_USAGE_EXAMPLES


def ingest_document(doc: LoadedDocument, force: bool) -> int:
    with connection() as conn, conn.transaction():
        existing = conn.execute("SELECT id, sha256 FROM rag.source_document WHERE code = %s AND version = %s",
                                (doc.code, doc.version)).fetchone()
        if existing and existing["sha256"] == doc.sha256 and not force:
            print(f"  = {doc.code} sin cambios (sha256), se omite")
            return 0
        if existing:
            conn.execute("DELETE FROM rag.source_document WHERE id = %s", (existing["id"],))

        chunks = hybrid_chunks(doc)
        vectors = embed_texts([c.embedding_text(doc.title) for c in chunks])
        document_id = conn.execute(
            """INSERT INTO rag.source_document (code, title, version, source_type, file_name, sha256, effective_date, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (doc.code, doc.title, doc.version, doc.source_type, doc.file_name, doc.sha256, doc.effective_date,
             Jsonb({"sections": len(doc.sections)})),
        ).fetchone()["id"]
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO rag.policy_chunk (document_id, chunk_index, section_path, content, token_count, embedding, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                [(document_id, i, c.section_path, c.content, c.token_count, v, Jsonb(c.metadata))
                 for i, (c, v) in enumerate(zip(chunks, vectors))],
            )
    kinds = {}
    for c in chunks:
        kinds[c.metadata["kind"]] = kinds.get(c.metadata["kind"], 0) + 1
    print(f"  + {doc.code} v{doc.version} [{doc.source_type}] -> {len(chunks)} chunks {kinds}")
    return len(chunks)


def rebuild_ivfflat_index() -> tuple[int, int]:
    """lists ~ sqrt(N) para corpus pequeño; se crea DESPUÉS de cargar (centroides sobre datos reales)."""
    with connection() as conn:
        total = conn.execute("SELECT count(*) AS n FROM rag.policy_chunk").fetchone()["n"]
        lists = max(1, round(math.sqrt(total)))
        conn.execute("DROP INDEX IF EXISTS rag.ix_policy_chunk_embedding_ivfflat")
        conn.execute(f"""CREATE INDEX ix_policy_chunk_embedding_ivfflat ON rag.policy_chunk
                         USING ivfflat (embedding vector_cosine_ops) WITH (lists = {lists})""")
        conn.execute("ANALYZE rag.policy_chunk")
    return total, lists


def ingest_tools() -> int:
    tools = fetch_all("SELECT code, description FROM core.tool WHERE active")
    texts = [f"{t['code']}: {t['description']} Ejemplos: {'; '.join(TOOL_USAGE_EXAMPLES.get(t['code'], []))}" for t in tools]
    vectors = embed_texts(texts)
    with connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO rag.tool_embedding (tool_code, description, usage_examples, embedding, updated_at)
               VALUES (%s, %s, %s, %s, now())
               ON CONFLICT (tool_code) DO UPDATE SET description = EXCLUDED.description,
                   usage_examples = EXCLUDED.usage_examples, embedding = EXCLUDED.embedding, updated_at = now()""",
            [(t["code"], t["description"], TOOL_USAGE_EXAMPLES.get(t["code"], []), v) for t, v in zip(tools, vectors)],
        )
    return len(tools)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()

    print(f"Ingesta de políticas desde {settings.policies_dir}")
    docs = load_all(settings.policies_dir)
    new_chunks = sum(ingest_document(doc, args.force) for doc in docs)
    total, lists = rebuild_ivfflat_index()
    tools = ingest_tools()
    print(f"Chunks nuevos: {new_chunks} | total: {total} | IVFFLAT lists={lists} (probes={settings.ivfflat_probes})")
    print(f"Tools embebidos: {tools} | {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
