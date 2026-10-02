# Evaluación del RAG

Generado por `backend/app/rag/eval_recall.py` el 2026-10-02 · 16 preguntas · k=4 · embeddings `text-embedding-3-small`.

| Estrategia | Chunks | Tokens/chunk | Recall@4 | MRR@4 | Regla completa@4 | Tokens contexto/consulta |
|---|---|---|---|---|---|---|
| Fijo 500/50 (scan exacto) | 12 | 398 | 0.88 | 0.78 | 0.88 | 1582 |
| Fijo 220/40 (scan exacto) | 27 | 196 | 1.00 | 0.83 | 0.94 | 829 |
| Híbrido (scan exacto) | 43 | 95 | 1.00 | 0.81 | 1.00 | 460 |
| Híbrido IVFFLAT lists=7 probes=1 | 43 | 95 | 1.00 | 0.81 | 1.00 | 460 |
| Híbrido IVFFLAT lists=7 probes=3 | 43 | 95 | 1.00 | 0.81 | 1.00 | 460 |
| Híbrido IVFFLAT lists=7 probes=7 | 43 | 95 | 1.00 | 0.81 | 1.00 | 460 |

**Cómo leerlo**
- *Recall@4*: la respuesta correcta (política + ancla) está entre los 4 primeros.
- *Regla completa@4*: algún chunk trae condición **y** consecuencia juntas (lo que necesita el agente para actuar).
- *Tokens contexto/consulta*: lo que se le enviaría al LLM; chunks grandes "aciertan" por cubrir medio documento,
  pero meten ruido y costo. El objetivo es alto recall con poco contexto.
- IVFFLAT con `probes = lists` equivale a scan exacto; el valor operativo elegido es `probes=3`.
