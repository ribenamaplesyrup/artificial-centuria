"""Survey execution."""

from dataclasses import dataclass

from centuria.llm import CostEstimate, complete, estimate_cost
from centuria.models import Persona, Question, QuestionResponse, Survey, SurveyResponse


SYSTEM_TEMPLATE = """You are {name}. Answer as this person would actually speak - casual, natural, in their own voice.

<context>
{context}
</context>

Guidelines:
- Speak naturally as this person would in real conversation - not formally or academically
- Reference specific details from your life, job, family, or daily routine
- Your opinions come from your personal experiences, not abstract values
- Be direct and concise - real people don't give speeches"""

USER_TEMPLATE_SINGLE_SELECT = """Question: {question}

Options: {options}

Reply in exactly this format:
CHOICE: [your chosen option]
JUSTIFICATION: [a short, personal reason in your own voice - mention something specific about your life, not generic benefits]

Bad example: "As someone who values community, this would bring people together."
Good example: "I'd use it every morning before my shift starts." or "My kids would love it, they're always asking for somewhere to play." """

USER_TEMPLATE_OPEN_ENDED = """Question: {question}

Provide a brief response."""


def build_system_prompt(persona: Persona) -> str:
    """Build the system prompt for a persona."""
    return SYSTEM_TEMPLATE.format(name=persona.name, context=persona.context)


def build_user_prompt(question: Question) -> str:
    """Build the user prompt for a question."""
    if question.question_type == "single_select" and question.options:
        return USER_TEMPLATE_SINGLE_SELECT.format(
            question=question.text,
            options=", ".join(question.options),
        )
    return USER_TEMPLATE_OPEN_ENDED.format(question=question.text)


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


async def ask_question(persona: Persona, question: Question, model: str | None = None) -> QuestionResponse:
    """Ask a persona a single question."""
    system = build_system_prompt(persona)
    user = build_user_prompt(question)
    result = await complete(user, system=system, model=model)

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
        # Single-select answers now include choice + justification (~30 tokens), open-ended longer (~50)
        est_completion = 30 if question.question_type == "single_select" else 50
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
