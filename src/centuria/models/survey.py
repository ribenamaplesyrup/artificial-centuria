"""Survey data models."""

from typing import Literal

from pydantic import BaseModel


class Question(BaseModel):
    """A survey question."""

    id: str
    text: str
    question_type: Literal["single_select", "open_ended"]
    options: list[str] | None = None  # For single_select


class Survey(BaseModel):
    """A collection of questions."""

    id: str
    name: str
    questions: list[Question]
