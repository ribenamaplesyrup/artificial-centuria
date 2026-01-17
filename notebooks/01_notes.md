# Notes: Silicon Sampling from Personal Data

## Literature & Terminology

The field uses various terms for LLM-based personas:
- "Silicon subject"
- "Synthetic user"
- "Silicon sample" (for a population of personas)

Source: Argyle et al., 2023

## Field Progress (as of 2026)

Key studies to review:
- X showed Y (placeholder for specific papers)

Open source projects:
- [AgentSociety](https://agentsociety.readthedocs.io/en/latest/index.html#) - Tsinghua's Future Intelligence Lab
- Smallville - Stanford researchers, observed surprising emergent dynamics

Companies with paying customers:
- [Artificial Societies](https://societies.io/)
- [Synthetic Users](https://www.syntheticusers.com/)

## Business Case

The value proposition is straightforward:
- **Time**: Months compressed to days
- **Cost**: No recruiting human participants
- **Quality**: Less accurate than humans, but enables scale not previously possible

Example pitch: "We can save you 1 year and £3 million on market research, delivering more extensive data testing across 3 additional product lines."

## Cultural Context

"Test culture before it happens" resonates in 2026. Related threads:
- Simulation as art/humor (The Rehearsal)
- Product demo becoming the technology
- Deepfake moment / pig butchering
- Repellant content that spreads (White House Ghibli memes, "nightmarish vulgar image" per Kissick)
- Computational philosophy building around Agentworld
- a16z involvement
- London artist-founder ecosystem

## Open Questions

- Could this be used on infrastructure?
- Could it work at single person or group level?
- "Premium grade slop" - quality concerns

## What Makes a Good Persona

Two key criteria:
1. **Accuracy** - Does it match the real person?
2. **Consistency** - Does it respond the same way across runs?

## Technical Notes

### Context Building

Current best practice (Gupta & Sheikh, 2026) favors **naturalistic backstories** over structured variable lists. Include:
- **Socio-demographics**: Age, profession, location, education
- **Psychographics**: Values, beliefs, orientations (if documented)
- **Issue covariates**: Prior experiences relevant to the questions you'll ask

### The Platform Problem

Different data sources create different personas:
- LinkedIn data → professionally optimistic, achievement-focused
- Twitter data → hot takes
- Neither is the "true self"

Cross-platform triangulation helps, but each source has its own presentation layer.

### Prompting

Start simple and add complexity only if it makes a significant difference (per Anthropic).

### Question Legitimacy

**Legitimate questions** (Forster, 2025) are those where the data provides direct evidence. Example: Asking about programming languages works because a CV lists technical skills.

**Illegitimate questions**: Those where no data exists (time of day preferences, lifestyle choices). The model will confabulate.

Example legitimacy analysis:

| Question | Legitimacy | Why |
|----------|------------|-----|
| Work alone vs team | Borderline | Data may not cover this; model will guess based on profession stereotype |
| Time of day | Illegitimate | Almost never in personal data; pure confabulation |
| Ideal weekend | Illegitimate | Lifestyle preferences rarely documented |

### Homogenization

Open-ended responses tend to sound like "a typical tech professional"—polished, optimistic, mentioning "impact." This is machine bias: the model generates the modal response for the profile, not the individual's actual voice.

### Validation (Argyle et al.)

**Algorithmic fidelity** criteria:
- **Backward continuity**: Does the silicon sample match known historical responses?
- **Forward continuity**: Does it predict future responses?
- **Pattern correspondence**: Does the distribution match real human distributions?

## Capabilities & Limitations

**What silicon samples can do:**
- Directional trends ("Will Group A prefer this over Group B?")
- Pilot testing survey questions before expensive human panels
- Theory generation and hypothesis development

**What they can't do reliably:**
- Point estimates ("Exactly 34.2% will vote for X")
- Minority/niche opinions (LLMs flatten identity groups to modal responses)
- Complex emotional reasoning or "feelings"

## Improvement Ideas

- Add issue covariates to context (not just demographics)
- Use naturalistic backstories instead of structured data dumps
- Design questions around what's actually documented
- Test for machine bias by including adversarial questions where LLM defaults conflict with known views
- Run multi-model validation (GPT-4 vs Claude) to detect model-specific confabulation

### Mitigating Homogenization

- Explicit grounding: "Answer ONLY based on evidence in the provided context"
- Contrastive prompting: "This person's view may differ from typical internet opinions"
- Calibrated uncertainty: Force the model to say "insufficient data" rather than guess
