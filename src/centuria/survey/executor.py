"""Survey execution."""

from centuria.llm import complete
from centuria.models import Persona, Question, QuestionResponse, Survey, SurveyResponse


def _build_prompt(persona: Persona, question: Question) -> str:
    """Build prompt for a question."""
    prompt = f"You are answering as {persona.name}.\n\n"
    prompt += f"Context about this person:\n{persona.context}\n\n"
    prompt += f"Question: {question.text}\n"

    if question.question_type == "single_select" and question.options:
        prompt += f"Options: {', '.join(question.options)}\n"
        prompt += "Reply with ONLY the option you choose, nothing else."
    else:
        prompt += "Provide a brief response."

    return prompt


async def ask_question(persona: Persona, question: Question, model: str | None = None) -> QuestionResponse:
    """Ask a persona a single question."""
    prompt = _build_prompt(persona, question)
    response = await complete(prompt, model=model)

    return QuestionResponse(
        question_id=question.id,
        response=response.strip(),
    )


async def run_survey(persona: Persona, survey: Survey, model: str | None = None) -> SurveyResponse:
    """Run a complete survey on a persona."""
    responses = []
    for question in survey.questions:
        response = await ask_question(persona, question, model=model)
        responses.append(response)

    return SurveyResponse(
        persona_id=persona.id,
        survey_id=survey.id,
        responses=responses,
    )
