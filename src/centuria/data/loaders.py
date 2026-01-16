"""Data loading utilities."""

from pathlib import Path

from pypdf import PdfReader


def load_text(path: str) -> str:
    """Load text from a file (.txt, .md, or .pdf)."""
    p = Path(path)

    if p.suffix.lower() == ".pdf":
        reader = PdfReader(p)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return p.read_text()


def load_files(paths: list[str]) -> str:
    """Load and combine text from multiple files."""
    texts = [load_text(p) for p in paths]
    return "\n\n".join(texts)
