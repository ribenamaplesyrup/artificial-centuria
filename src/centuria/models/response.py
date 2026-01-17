"""Response data models."""

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    """Response to a single question."""

    question_id: str
    response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0  # USD


class SurveyResponse(BaseModel):
    """Complete survey response from a persona."""

    persona_id: str
    survey_id: str
    responses: list[QuestionResponse]

    @property
    def total_tokens(self) -> int:
        """Total tokens used across all questions."""
        return sum(r.prompt_tokens + r.completion_tokens for r in self.responses)

    @property
    def total_cost(self) -> float:
        """Total cost in USD across all questions."""
        return sum(r.cost for r in self.responses)
