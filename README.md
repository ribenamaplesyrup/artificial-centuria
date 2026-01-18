# Artificial Centuria

Generate 100+ LLM personas to model groups of humans and survey them on single-select and open-ended questions.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone this repository
3. Copy `.env.example` to `.env` and add your API keys
4. Install dependencies:

```bash
uv sync
```

5. Launch Jupyter Lab:

```bash
uv run jupyter lab
```

## Project Structure

```
artificial-centuria/
├── notebooks/           # Experimentation notebooks
├── src/centuria/        # Core library
│   ├── models/          # Pydantic data models
│   ├── llm/             # LiteLLM client & prompts
│   ├── persona/         # Persona generation
│   ├── survey/          # Survey execution & analysis
│   ├── data/            # Data loading utilities
│   └── observability/   # Cost tracking
├── web/                 # SvelteKit web application
├── data/                # User data (gitignored)
├── surveys/             # Survey definitions (YAML)
└── tests/               # Unit tests
```

## Quick Start

```python
from centuria.persona import PersonaGenerator
from centuria.survey import SurveyExecutor

# Generate a persona from your data
generator = PersonaGenerator()
persona = await generator.from_files(["cv.pdf", "linkedin.txt"])

# Run a survey
executor = SurveyExecutor()
responses = await executor.run(persona, survey)
```

## Web App

The project includes a SvelteKit web application for visualizing survey results.

### Running the Web App

1. Start the Python API server:
```bash
uv run python -m centuria.api.server
```

2. In a separate terminal, navigate to the web directory and install dependencies:
```bash
cd web
npm install
```

3. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

### Building for Production

```bash
npm run build
npm run preview  # Preview the production build
```

## Development

Run tests:
```bash
uv run pytest
```

## License

MIT
