"""Comparación de nombres declarados vs Registro Civil (POL-KYC-001 Art. 5)."""
import unicodedata

from rapidfuzz import fuzz


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def name_match_score(declared: str, registered: str) -> float:
    """Fracción de tokens declarados presentes (fuzzy) en el nombre registrado.

    Tolera nombres parciales: "Juan Perez" vs "Juan Andrés Pérez Molina" = 1.0.
    """
    declared_tokens = normalize(declared).split()
    registered_tokens = normalize(registered).split()
    if not declared_tokens or not registered_tokens:
        return 0.0
    hits = 0.0
    for token in declared_tokens:
        best = max(fuzz.ratio(token, candidate) for candidate in registered_tokens) / 100
        hits += best if best >= 0.8 else 0.0
    return round(hits / len(declared_tokens), 3)


def first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0].capitalize() if parts else ""
