"""Chunking híbrido: estructural -> semántico + encabezado contextual (docs/rag/PIPELINE_RAG.md).

Nivel 1 (estructural) lo hace loaders.py (artículos / secciones).
Nivel 2 (semántico): si una sección supera MAX_TOKENS, se agrupan sus párrafos contiguos y se corta donde la
distancia coseno entre párrafos consecutivos supera el percentil BREAKPOINT_PERCENTILE (o si el grupo excede
MAX_TOKENS). Un párrafo que solo ya excede el tope se parte por oraciones con embedding de ventana deslizante.
Tablas: un chunk por fila con el encabezado repetido.
"""
import re
from dataclasses import dataclass, field

import numpy as np
import tiktoken

from app.rag.embeddings import embed_texts
from app.rag.loaders import LoadedDocument

MAX_TOKENS = 220
MIN_TOKENS = 40
BREAKPOINT_PERCENTILE = 90
SHORT_SENTENCE_TOKENS = 10
WINDOW = 1

_encoder = tiktoken.get_encoding("cl100k_base")
_SENTENCE_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


@dataclass
class Chunk:
    section_path: str
    content: str
    metadata: dict = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return count_tokens(self.content)

    def embedding_text(self, title: str) -> str:
        """Encabezado contextual: el vector 'sabe' de qué política y artículo viene el texto."""
        return f"{title} | {self.section_path}\n{self.content}"


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _table_rows_to_chunks(rows: list[str], path: str) -> list[Chunk]:
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header, chunks = cells(rows[0]), []
    for row in rows[1:]:
        values = cells(row)
        content = ". ".join(f"{h}: {v}" for h, v in zip(header, values)) + "."
        chunks.append(Chunk(f"{path} > {values[0]}", content, {"kind": "table_row"}))
    return chunks


def _merge_short_sentences(sentences: list[str]) -> list[str]:
    """Une oraciones-etiqueta ("Riesgo alto.") con la siguiente: solas solo agregan ruido a las distancias."""
    units: list[str] = []
    carry = ""
    for sentence in sentences:
        sentence = f"{carry} {sentence}".strip() if carry else sentence
        if count_tokens(sentence) < SHORT_SENTENCE_TOKENS:
            carry = sentence
            continue
        carry = ""
        units.append(sentence)
    if carry:
        units.append(carry) if not units else units.__setitem__(-1, units[-1] + " " + carry)
    return units


def _window_vectors(units: list[str]) -> list[np.ndarray]:
    """Embedding de ventana deslizante (anterior + actual + siguiente) para suavizar la señal de distancia."""
    windows = [" ".join(units[max(0, i - WINDOW):i + WINDOW + 1]) for i in range(len(units))]
    return embed_texts(windows)


def _distances(vectors: list[np.ndarray]) -> np.ndarray:
    return np.array([1 - float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
                     for a, b in zip(vectors, vectors[1:])])


def _group_by_breakpoints(units: list[str], distances: np.ndarray) -> list[list[str]]:
    """Agrupa unidades contiguas; corta donde la distancia >= percentil o si el grupo excede MAX_TOKENS."""
    threshold = np.percentile(distances, BREAKPOINT_PERCENTILE)
    groups, current = [], [units[0]]
    for unit, distance in zip(units[1:], distances):
        if distance >= threshold or count_tokens(" ".join(current + [unit])) > MAX_TOKENS:
            groups.append(current)
            current = []
        current.append(unit)
    groups.append(current)
    return groups


def _sentence_groups(paragraph: str) -> list[str]:
    """Párrafo más largo que MAX_TOKENS: oraciones con embedding de ventana deslizante."""
    units = _merge_short_sentences(split_sentences(paragraph))
    if len(units) < 2:
        return units
    return [" ".join(g) for g in _group_by_breakpoints(units, _distances(_window_vectors(units)))]


def _semantic_groups(paragraphs: list[str]) -> list[list[str]]:
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(_sentence_groups(paragraph) if count_tokens(paragraph) > MAX_TOKENS else [paragraph])
    if len(units) < 2:
        return [units]
    return _group_by_breakpoints(units, _distances(embed_texts(units)))


def _merge_small(chunks: list[Chunk]) -> list[Chunk]:
    """Une chunks < MIN_TOKENS con el anterior de la MISMA sección (no cruza artículos)."""
    merged: list[Chunk] = []
    for chunk in chunks:
        if merged and chunk.token_count < MIN_TOKENS and merged[-1].section_path == chunk.section_path:
            merged[-1].content += " " + chunk.content
        elif merged and merged[-1].token_count < MIN_TOKENS and merged[-1].section_path == chunk.section_path:
            merged[-1].content += " " + chunk.content
        else:
            merged.append(chunk)
    return merged


def hybrid_chunks(doc: LoadedDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in doc.sections:
        path = f"{doc.code} > {section.heading}"
        table_rows = [p for p in section.paragraphs if p.startswith("|")]
        paragraphs = [p for p in section.paragraphs if not p.startswith("|")]
        text = " ".join(paragraphs)

        if text:
            if count_tokens(text) <= MAX_TOKENS:
                chunks.append(Chunk(path, text, {"kind": "section"}))
            else:
                parts = _semantic_groups(paragraphs)
                section_chunks = [Chunk(path, " ".join(p), {"kind": "semantic", "part": i + 1, "parts": len(parts)})
                                  for i, p in enumerate(parts)]
                chunks.extend(_merge_small(section_chunks))
        if table_rows:
            chunks.extend(_table_rows_to_chunks(table_rows, path))

    for chunk in chunks:
        chunk.metadata.update({"policy_code": doc.code})
    return chunks


def fixed_chunks(doc: LoadedDocument, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Línea base para la evaluación: ventanas de tokens de tamaño fijo con solapamiento."""
    tokens = _encoder.encode(doc.full_text)
    chunks, start, i = [], 0, 0
    while start < len(tokens):
        window = tokens[start:start + size]
        chunks.append(Chunk(f"{doc.code} > fixed#{i}", _encoder.decode(window), {"policy_code": doc.code}))
        start += size - overlap
        i += 1
    return chunks
