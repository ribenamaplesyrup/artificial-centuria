"""Persona generation."""

import uuid

from centuria.data import load_files
from centuria.models import Persona


def create_persona(name: str, context: str, persona_id: str | None = None) -> Persona:
    """Create a persona from context text."""
    return Persona(
        id=persona_id or str(uuid.uuid4()),
        name=name,
        context=context,
    )


def create_persona_from_files(name: str, paths: list[str]) -> Persona:
    """Create a persona from data files."""
    context = load_files(paths)
    return create_persona(name=name, context=context)
