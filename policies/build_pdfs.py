"""Genera policies/docs/ a partir de policies/src/.

Las políticas POL-KYC-001 y POL-PLA-002 se publican como PDF (para demostrar ingesta de PDF real);
el resto se copia tal cual (md / txt).

Uso: cd backend && uv run python ../policies/build_pdfs.py
"""
import shutil
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent
SRC, OUT = ROOT / "src", ROOT / "docs"
AS_PDF = {"POL-KYC-001.md", "POL-PLA-002.md"}


def to_pdf(src: Path, dst: Path) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5, leading=14, alignment=TA_JUSTIFY)
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=15, leading=19)
    article = ParagraphStyle("article", parent=styles["Heading3"], fontSize=11.5, spaceBefore=8)

    story = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            story += [Paragraph(line[2:], title), Spacer(1, 0.3 * cm)]
        elif line.startswith("Artículo "):
            story.append(Paragraph(line, article))
        else:
            story += [Paragraph(line, body), Spacer(1, 0.15 * cm)]

    doc = SimpleDocTemplate(str(dst), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=src.stem, author="Banco Andino Demo")
    doc.build(story)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for src in sorted(SRC.iterdir()):
        if src.name in AS_PDF:
            dst = OUT / f"{src.stem}.pdf"
            to_pdf(src, dst)
        else:
            dst = OUT / src.name
            shutil.copyfile(src, dst)
        print(f"  {src.name} -> docs/{dst.name}")


if __name__ == "__main__":
    main()
