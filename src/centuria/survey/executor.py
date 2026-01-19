"""Survey execution."""

import asyncio
from dataclasses import dataclass

from centuria.llm import CostEstimate, complete, estimate_cost
from centuria.models import Persona, Question, QuestionResponse, Survey, SurveyResponse

# =============================================================================
# Survey Prompts
# =============================================================================

SURVEY_SYSTEM_PROMPT = """You are {name}. Answer as this person would actually speak - casual, natural, in their own voice.

<context>
{context}
</context>

Guidelines:
- Speak naturally as this person would in real conversation - not formally or academically
- Reference specific details from your life, job, family, or daily routine
- Your opinions come from your personal experiences, not abstract values
- Be direct and concise - real people don't give speeches"""

SURVEY_USER_PROMPT_SINGLE_SELECT = """Question: {question}

Options: {options}

Reply in exactly this format:
CHOICE: [your chosen option]
JUSTIFICATION: [a short, personal reason in your own voice - reference something specific from your life, work, or daily routine]

Bad example: "I believe this aligns with my values of sustainability and community."
Good example: "I deal with this at work every day" or "Tried it last year and it was a nightmare" or "My brother-in-law won't shut up about it" """

SURVEY_USER_PROMPT_OPEN_ENDED = """Question: {question}

Provide a brief response."""

# Estimated completion tokens for cost estimation
SURVEY_COMPLETION_TOKENS_SINGLE_SELECT = 30
SURVEY_COMPLETION_TOKENS_OPEN_ENDED = 50


def build_system_prompt(persona: Persona) -> str:
    """Build the system prompt for a persona."""
    return SURVEY_SYSTEM_PROMPT.format(name=persona.name, context=persona.context)


def build_user_prompt(question: Question) -> str:
    """Build the user prompt for a question."""
    if question.question_type == "single_select" and question.options:
        return SURVEY_USER_PROMPT_SINGLE_SELECT.format(
            question=question.text,
            options=", ".join(question.options),
        )
    return SURVEY_USER_PROMPT_OPEN_ENDED.format(question=question.text)


def parse_choice_and_justification(content: str) -> tuple[str, str]:
    """Parse CHOICE and JUSTIFICATION from a structured response."""
    lines = content.strip().split("\n")
    choice = ""
    justification = ""

    for line in lines:
        line = line.strip()
        if line.upper().startswith("CHOICE:"):
            choice = line[7:].strip()
        elif line.upper().startswith("JUSTIFICATION:"):
            justification = line[14:].strip()

    # Fallback: if no structured response, treat entire content as choice
    if not choice:
        choice = content.strip()

    return choice, justification


async def ask_question(
    persona: Persona,
    question: Question,
    model: str | None = None,
    api_keys: dict[str, str] | None = None,
) -> QuestionResponse:
    """Ask a persona a single question."""
    system = build_system_prompt(persona)
    user = build_user_prompt(question)
    result = await complete(user, system=system, model=model, api_keys=api_keys)

    # Parse choice and justification for single_select questions
    if question.question_type == "single_select":
        choice, justification = parse_choice_and_justification(result.content)
    else:
        choice = result.content.strip()
        justification = ""

    return QuestionResponse(
        question_id=question.id,
        response=choice,
        justification=justification,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost=result.cost,
    )


async def run_survey(
    persona: Persona,
    survey: Survey,
    model: str | None = None,
    api_keys: dict[str, str] | None = None,
) -> SurveyResponse:
    """Run a complete survey on a persona (all questions in parallel)."""
    # Run all questions in parallel for speed
    responses = await asyncio.gather(*[
        ask_question(persona, question, model=model, api_keys=api_keys)
        for question in survey.questions
    ])

    return SurveyResponse(
        persona_id=persona.id,
        survey_id=survey.id,
        responses=list(responses),
    )


@dataclass
class SurveyEstimate:
    """Estimated cost for running a survey."""

    prompt_tokens: int
    completion_tokens: int
    cost_per_agent: float
    num_agents: int

    @property
    def total_cost(self) -> float:
        return self.cost_per_agent * self.num_agents


def estimate_survey_cost(
    persona: Persona,
    survey: Survey,
    num_agents: int = 1,
    model: str | None = None,
) -> SurveyEstimate:
    """
    Estimate the cost of running a survey before executing it.

    Args:
        persona: The persona (used to estimate context size)
        survey: The survey to run
        num_agents: Number of agents to run the survey on
        model: Model to use

    Returns:
        SurveyEstimate with token counts and costs
    """
    system = build_system_prompt(persona)
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0

    for question in survey.questions:
        user = build_user_prompt(question)
        est_completion = (
            SURVEY_COMPLETION_TOKENS_SINGLE_SELECT
            if question.question_type == "single_select"
            else SURVEY_COMPLETION_TOKENS_OPEN_ENDED
        )
        estimate = estimate_cost(user, system=system, model=model, estimated_completion_tokens=est_completion)

        total_prompt_tokens += estimate.prompt_tokens
        total_completion_tokens += estimate.completion_tokens
        total_cost += estimate.cost

    return SurveyEstimate(
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
        cost_per_agent=total_cost,
        num_agents=num_agents,
    )
