"""Evaluación del RAG: chunking (fijo vs híbrido) e índice (IVFFLAT vs scan exacto).

Uso: uv run python -m app.rag.eval_recall      -> imprime y escribe docs/rag/EVALUACION_RAG.md

Métricas @k=4:
  recall      : alguna de las k respuestas es de la política esperada y contiene el ancla
  mrr         : 1/posición del primer acierto
  regla       : algún chunk recuperado contiene TODOS los términos de la regla (condición + consecuencia)
  tokens_ctx  : tokens promedio que se entregarían al LLM (costo / ruido de contexto)
"""
from datetime import date

import numpy as np

from app.config import REPO_ROOT, settings
from app.db.pool import fetch_one
from app.domain.names import normalize
from app.rag.chunking import count_tokens, fixed_chunks
from app.rag.embeddings import embed_text, embed_texts
from app.rag.loaders import load_all
from app.rag.retriever import search_policies

K = 4

# (pregunta, política esperada, ancla, términos de la regla completa) - normalizados sin tildes
QUESTIONS = [
    ("¿Qué nivel de confianza mínimo se requiere para verificar la identidad?", "POL-KYC-001", "0.80", ["0.80", "agencia"]),
    ("¿Cómo se calcula el dígito verificador de la cédula?", "POL-KYC-001", "modulo 10", ["modulo 10", "coeficientes"]),
    ("¿Qué pasa si el número de cédula no es válido?", "POL-KYC-001", "no cumple estas reglas", ["no cumple", "rechaza"]),
    ("¿Qué edad mínima debe tener el cliente para abrir una cuenta en línea?", "POL-KYC-001", "18 anos", ["18 anos", "representante legal"]),
    ("¿Qué se hace si la persona consta como fallecida?", "POL-KYC-001", "fallecida", ["fallecida", "agencia"]),
    ("¿Qué listas de control se deben consultar antes de vincular?", "POL-PLA-002", "ofac", ["ofac", "uafe"]),
    ("¿Qué nivel de riesgo tiene una Persona Expuesta Políticamente?", "POL-PLA-002", "riesgo medio", ["personas expuestas politicamente", "debida diligencia reforzada"]),
    ("¿Qué información se le pide a un cliente con riesgo medio?", "POL-PLA-002", "origen de los fondos", ["actividad economica", "origen de los fondos"]),
    ("¿Se puede informar al cliente que fue identificado en una lista de control?", "POL-PLA-002", "prohibido informar", ["prohibido", "generico"]),
    ("¿Qué pasa si el servicio de listas de control no responde?", "POL-PLA-002", "no responde", ["no responde", "no puede aprobarse"]),
    ("¿Qué documentos necesito para abrir una cuenta corriente?", "POL-PRD-003", "cuenta corriente", ["referencia bancaria", "firma electronica"]),
    ("¿Cuál es el monto mínimo de un depósito a plazo fijo?", "POL-PRD-003", "1.000", ["1.000", "31 dias"]),
    ("¿A qué área se escala un cliente con riesgo alto?", "POL-ESC-004", "cumplimiento", ["cumplimiento", "48 horas"]),
    ("¿Qué pasa si falla la creación del usuario de banca digital después de aprobar?", "POL-ESC-004", "acceso digital", ["aprobada", "24 horas"]),
    ("¿Qué frase se usa en los mensajes de rechazo al cliente?", "POL-COM-005", "por temas de politicas", ["por temas de politicas del banco"]),
    ("¿Cuántos dígitos de la cédula se pueden mostrar al cliente?", "POL-COM-005", "cuatro digitos", ["ultimos cuatro digitos"]),
]


def score(results: list[dict]) -> dict:
    recall = mrr = rule = 0.0
    tokens = 0
    for (question, code, anchor, rule_terms), retrieved in zip(QUESTIONS, results):
        texts = [normalize(r["content"]) for r in retrieved]
        tokens += sum(count_tokens(r["content"]) for r in retrieved)
        for rank, (r, text) in enumerate(zip(retrieved, texts), start=1):
            if r["policy_code"] == code and anchor in text:
                recall += 1
                mrr += 1 / rank
                break
        if any(all(term in text for term in rule_terms) for text in texts):
            rule += 1
    n = len(QUESTIONS)
    return {"recall": recall / n, "mrr": mrr / n, "regla": rule / n, "tokens_ctx": tokens / n}


def in_memory_strategy(size: int, overlap: int) -> tuple[list[list[dict]], int, float]:
    docs = load_all(settings.policies_dir)
    chunks = [(doc, c) for doc in docs for c in fixed_chunks(doc, size, overlap)]
    matrix = np.vstack(embed_texts([f"{d.title} | {d.code}\n{c.content}" for d, c in chunks]))
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    results = []
    for question, *_ in QUESTIONS:
        q = embed_text(question)
        sims = matrix @ (q / np.linalg.norm(q))
        top = np.argsort(-sims)[:K]
        results.append([{"policy_code": chunks[i][1].metadata["policy_code"], "content": chunks[i][1].content,
                         "score": float(sims[i])} for i in top])
    return results, len(chunks), float(np.mean([c.token_count for _, c in chunks]))


def db_strategy(**kwargs) -> list[list[dict]]:
    return [search_policies(q, top_k=K, min_score=0, **kwargs) for q, *_ in QUESTIONS]


def main() -> None:
    stats = fetch_one("SELECT count(*) AS n, avg(token_count) AS avg FROM rag.policy_chunk")
    lists = int(fetch_one("""SELECT (regexp_match(indexdef, 'lists=''?(\\d+)'))[1] AS l FROM pg_indexes
                             WHERE indexname = 'ix_policy_chunk_embedding_ivfflat'""")["l"])
    rows = []

    for size, overlap in [(500, 50), (220, 40)]:
        res, n, avg = in_memory_strategy(size, overlap)
        rows.append((f"Fijo {size}/{overlap} (scan exacto)", n, avg, score(res)))
    rows.append(("Híbrido (scan exacto)", stats["n"], float(stats["avg"]), score(db_strategy(exact=True))))
    for probes in sorted({1, settings.ivfflat_probes, lists}):
        rows.append((f"Híbrido IVFFLAT lists={lists} probes={probes}", stats["n"], float(stats["avg"]),
                     score(db_strategy(probes=probes))))

    header = "| Estrategia | Chunks | Tokens/chunk | Recall@4 | MRR@4 | Regla completa@4 | Tokens contexto/consulta |\n|---|---|---|---|---|---|---|"
    lines = [f"| {name} | {n} | {avg:.0f} | {m['recall']:.2f} | {m['mrr']:.2f} | {m['regla']:.2f} | {m['tokens_ctx']:.0f} |"
             for name, n, avg, m in rows]
    table = "\n".join([header, *lines])
    print(table)

    out = REPO_ROOT / "docs" / "rag" / "EVALUACION_RAG.md"
    out.write_text(f"""# Evaluación del RAG

Generado por `backend/app/rag/eval_recall.py` el {date.today().isoformat()} · {len(QUESTIONS)} preguntas · k={K} · embeddings `{settings.embedding_model}`.

{table}

**Cómo leerlo**
- *Recall@4*: la respuesta correcta (política + ancla) está entre los 4 primeros.
- *Regla completa@4*: algún chunk trae condición **y** consecuencia juntas (lo que necesita el agente para actuar).
- *Tokens contexto/consulta*: lo que se le enviaría al LLM; chunks grandes "aciertan" por cubrir medio documento,
  pero meten ruido y costo. El objetivo es alto recall con poco contexto.
- IVFFLAT con `probes = lists` equivale a scan exacto; el valor operativo elegido es `probes={settings.ivfflat_probes}`.
""", encoding="utf-8")
    print(f"\nEscrito {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
