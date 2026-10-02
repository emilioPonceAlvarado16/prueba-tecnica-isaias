# Pipeline RAG

`./manage_env.sh rag:ingest` → `policies/build_pdfs.py` + `python -m app.rag.ingest`

| Etapa | Implementación | Archivo |
|---|---|---|
| Ingesta | PDF (pypdf modo layout, conserva párrafos), MD, TXT; idempotente por `sha256` | `rag/loaders.py` |
| Chunking | Híbrido: estructural (artículo/sección) → semántico por párrafos (percentil 90 de distancia coseno, tope 220 tokens) → oraciones con ventana deslizante si un párrafo excede; tablas = 1 chunk por fila | `rag/chunking.py` |
| Embeddings | `text-embedding-3-small` (1536) con encabezado contextual `título \| sección`; caché en disco | `rag/embeddings.py` |
| Almacenamiento | `rag.policy_chunk.embedding vector(1536)` | `rag/ingest.py` |
| Índice | IVFFLAT `vector_cosine_ops`, creado después de la carga, `lists = √N` (43 chunks → 7), `probes = 3`, `iterative_scan` | `rag/ingest.py`, `rag/retriever.py` |
| Recuperación | Coseno `<=>`, filtro por política, top-4, score mínimo 0.30, log en `rag.retrieval_log` | `rag/retriever.py` |
| RAG de tools | Descripción + ejemplos de cada tool embebidos; scan exacto | `rag/tool_retriever.py` |
| Evaluación | 16 preguntas: fijo 500/50 y 220/40 vs híbrido; IVFFLAT vs exacto → [EVALUACION_RAG.md](EVALUACION_RAG.md) | `rag/eval_recall.py` |

Corpus: 5 políticas en `policies/src` (2 PDF, 2 MD, 1 TXT) → 43 chunks (35 por sección, 5 semánticos, 3 filas de tabla).
