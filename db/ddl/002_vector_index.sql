-- Ejecutar DESPUÉS de la ingesta RAG (manage_env.sh rag:ingest lo hace automáticamente).
-- lists ~ sqrt(N) para N pequeño (PoC ~100-150 chunks). La regla N/1000 de pgvector aplica a tablas grandes.
-- probes se fija por sesión en el retriever: SET LOCAL ivfflat.probes = 3  (~ sqrt(lists)).
DROP INDEX IF EXISTS rag.ix_policy_chunk_embedding_ivfflat;
CREATE INDEX ix_policy_chunk_embedding_ivfflat
    ON rag.policy_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
ANALYZE rag.policy_chunk;
