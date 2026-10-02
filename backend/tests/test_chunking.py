from app.config import settings
from app.rag.chunking import MAX_TOKENS, hybrid_chunks
from app.rag.loaders import load_all


def test_chunks_respetan_estructura_y_tope():
    docs = {d.code: d for d in load_all(settings.policies_dir)}
    assert set(docs) == {"POL-KYC-001", "POL-PLA-002", "POL-PRD-003", "POL-ESC-004", "POL-COM-005"}
    assert docs["POL-KYC-001"].source_type == "pdf"
    for doc in docs.values():
        for chunk in hybrid_chunks(doc):
            assert chunk.section_path.startswith(doc.code)
            assert chunk.token_count <= MAX_TOKENS + 40


def test_tabla_un_chunk_por_producto():
    doc = next(d for d in load_all(settings.policies_dir) if d.code == "POL-PRD-003")
    rows = [c for c in hybrid_chunks(doc) if c.metadata["kind"] == "table_row"]
    assert [r.section_path.split(" > ")[-1] for r in rows] == ["Cuenta de ahorros", "Cuenta corriente",
                                                              "Depósito a plazo fijo"]


def test_regla_de_confianza_completa_en_un_chunk():
    doc = next(d for d in load_all(settings.policies_dir) if d.code == "POL-KYC-001")
    art4 = [c.content for c in hybrid_chunks(doc) if "Artículo 4" in c.section_path]
    assert any("0.80" in text and "agencia" in text for text in art4)
