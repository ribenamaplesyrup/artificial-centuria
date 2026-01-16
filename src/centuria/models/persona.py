"""Persona data models."""

from pydantic import BaseModel


class Persona(BaseModel):
    """A persona representing a human."""

    id: str
    name: str
    context: str  # The raw text data used to represent this person
