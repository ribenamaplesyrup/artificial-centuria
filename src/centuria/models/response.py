"""Response data models."""

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    """Response to a single question."""

    question_id: str
    response: str


class SurveyResponse(BaseModel):
    """Complete survey response from a persona."""

    persona_id: str
    survey_id: str
    responses: list[QuestionResponse]
