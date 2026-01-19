# Artificial Centuria

Experiments using LLMs to generate synthetic personas and survey them. Includes notebooks exploring methods and a web app for interactive experiments.

## Project Structure

```
artificial-centuria/
├── src/centuria/           # Core API library
│   ├── api/server.py       # FastAPI endpoints
│   ├── config.py           # Prompts & configuration (single source of truth)
│   ├── utils.py            # Shared utilities
│   ├── llm/                # LLM client wrapper (LiteLLM)
│   ├── persona/            # Persona generation
│   │   ├── synthetic.py    # Generation logic
│   │   └── file_types.py   # 40 file type definitions
│   ├── survey/             # Survey execution
│   ├── data/               # Data loading & extraction
│   └── models/             # Pydantic models
├── notebooks/              # Jupyter notebooks (3 experiments)
├── web/                    # SvelteKit webapp
├── data/
│   ├── personal/           # Your personal data (gitignored)
│   └── synthetic/          # Generated personas for experiments
└── tests/                  # Test suite
```

## Notebooks

The `notebooks/` directory contains Jupyter notebooks that walk through the core features:

- **`01_single_agent_from_personal_data.ipynb`**: Creates an LLM persona from personal data (like a CV) and tests its accuracy against real answers. Compares structured vs. unstructured data approaches.

- **`02_synthetic_persona_generation.ipynb`**: Details creating synthetic personas - extracting profiles, dealing with LLM biases, and a "file-first" approach where data files are generated before the persona.

- **`03_building_a_fictional_neighbourhood.ipynb`**: Generates 100 synthetic personas for a fictional E8 London neighbourhood based on real census data.

## Web App

The `web/` directory contains a SvelteKit application with two interactive experiments:

- **`01-random-person-generator`**: Generates random personas and displays them on a map with population statistics, highlighting LLM biases in random generation.

- **`02-testing-space-before-it-happens`**: Simulates a community in Dalston deciding what to do with collectively owned land. Surveys 100 synthetic personas, visualizes results, and generates an AI image of the final vision.

### Running Locally

1. **Set up environment variables** (if not already done):
   ```bash
   cp .env.example .env
   # Add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY)
   ```

2. **Start the API server:**
   ```bash
   uv run python -m centuria.api.server
   ```
   The server runs on port 8000 by default. If that port is in use, specify a different one:
   ```bash
   PORT=8001 uv run python -m centuria.api.server
   ```

3. **In another terminal, run the web app:**
   ```bash
   cd web
   npm install
   npm run dev
   ```
   The web app runs on port 5173 (or the next available port).

4. **Open the app** at http://localhost:5173

## Getting Started

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)**

2. **Clone the repository**

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
   ```

4. **Install dependencies:**
   ```bash
   uv sync
   ```

5. **Explore the notebooks:**
   ```bash
   uv run jupyter lab
   ```

## Configuration

All prompts and configuration live in `src/centuria/config.py`:
- LLM provider/model settings
- Persona generation prompts
- Survey prompts
- Age thresholds for file type selection
- Occupation categories

## License

MIT
