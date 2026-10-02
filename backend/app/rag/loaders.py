"""Ingesta: lectura de PDF / Markdown / TXT a secciones estructurales.

Nivel 1 del chunking (estructural): cada documento se divide en secciones según su formato:
  - PDF:  líneas "Artículo N. Título"
  - MD:   encabezados "## ..."
  - TXT:  líneas "SECCIÓN N. Título"
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pypdf import PdfReader

MONTHS = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}

HEADING_PATTERNS = {
    "pdf": re.compile(r"^(Artículo \d+\..*)$"),
    "md": re.compile(r"^##\s+(.*)$"),
    "txt": re.compile(r"^(SECCIÓN \d+\..*)$"),
}


@dataclass
class Section:
    heading: str
    paragraphs: list[str] = field(default_factory=list)   # párrafos o filas de tabla ("|...|")


@dataclass
class LoadedDocument:
    code: str
    title: str
    version: str
    effective_date: date
    source_type: str
    file_name: str
    sha256: str
    sections: list[Section]

    @property
    def full_text(self) -> str:
        parts = []
        for s in self.sections:
            parts.append(s.heading)
            parts.extend(s.paragraphs)
        return "\n".join(parts)


def _raw_lines(path: Path, source_type: str) -> list[str]:
    if source_type == "pdf":
        # modo layout: conserva líneas en blanco entre párrafos (el modo plano las pierde)
        text = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in PdfReader(path).pages)
    else:
        text = path.read_text(encoding="utf-8")
    return [" ".join(line.split()) for line in text.splitlines()]


def _to_sections(lines: list[str], source_type: str) -> tuple[str, list[Section]]:
    pattern = HEADING_PATTERNS[source_type]
    title = lines[0].lstrip("# ").strip()
    sections = [Section(heading="Encabezado")]
    buffer: list[str] = []

    def flush():
        if buffer:
            sections[-1].paragraphs.append(" ".join(buffer))
            buffer.clear()

    for line in lines[1:]:
        stripped = line.strip()
        match = pattern.match(stripped)
        if match:
            flush()
            sections.append(Section(heading=match.group(1).strip()))
        elif not stripped:
            flush()
        elif stripped.startswith("|"):
            flush()
            if not re.fullmatch(r"\|[\s\-|:]+\|", stripped):      # descarta la fila separadora |---|
                sections[-1].paragraphs.append(stripped)
        elif source_type == "pdf":
            buffer.append(stripped)       # el PDF parte párrafos en varias líneas: se re-unen
        else:
            flush()
            buffer.append(stripped)
    flush()
    return title, [s for s in sections if s.paragraphs]


def load_document(path: Path) -> LoadedDocument:
    source_type = path.suffix.lstrip(".").lower()
    lines = _raw_lines(path, source_type)
    title, sections = _to_sections(lines, source_type)

    header = " ".join(sections[0].paragraphs) if sections else ""
    code = re.match(r"(POL-[A-Z]+-\d{3})", title).group(1)
    version = (re.search(r"Versión (\d+\.\d+)", header) or re.search(r"(\d+\.\d+)", "1.0")).group(1)
    date_match = re.search(r"Vigente desde el (\d{1,2}) de (\w+) de (\d{4})", header)
    effective = (date(int(date_match.group(3)), MONTHS[date_match.group(2).lower()], int(date_match.group(1)))
                 if date_match else date.today())
    return LoadedDocument(
        code=code,
        title=title.replace(code, "").strip(),
        version=version,
        effective_date=effective,
        source_type=source_type,
        file_name=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        sections=sections,
    )


def load_all(directory: Path) -> list[LoadedDocument]:
    return [load_document(p) for p in sorted(directory.iterdir()) if p.suffix.lower() in {".pdf", ".md", ".txt"}]
