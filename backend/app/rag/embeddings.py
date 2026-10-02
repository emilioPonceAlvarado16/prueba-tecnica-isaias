"""Cliente de embeddings OpenAI con caché en disco (re-ingesta determinística y sin costo repetido)."""
import hashlib
import shelve
import threading

import numpy as np
from openai import OpenAI

from app.config import settings

_BATCH = 96
_lock = threading.Lock()
_client: OpenAI | None = None


def _openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key, timeout=20, max_retries=2)
    return _client


def _key(text: str) -> str:
    return hashlib.sha256(f"{settings.embedding_model}\x00{text}".encode()).hexdigest()


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    results: dict[int, np.ndarray] = {}
    with _lock, shelve.open(str(settings.cache_dir / "embeddings")) as cache:
        missing = []
        for i, text in enumerate(texts):
            cached = cache.get(_key(text))
            if cached is not None:
                results[i] = np.asarray(cached, dtype=np.float32)
            else:
                missing.append(i)
        for start in range(0, len(missing), _BATCH):
            batch = missing[start:start + _BATCH]
            response = _openai().embeddings.create(model=settings.embedding_model, input=[texts[i] for i in batch])
            for i, item in zip(batch, response.data):
                vector = np.asarray(item.embedding, dtype=np.float32)
                cache[_key(texts[i])] = vector.tolist()
                results[i] = vector
    return [results[i] for i in range(len(texts))]


def embed_text(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
