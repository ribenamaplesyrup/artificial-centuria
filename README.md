# Artificial Centuria

This project includes some basic experiments using LLMs to generate synthetic personas and surveying them. It includes notebooks exploring methods and a web app simulating experiments.

## Key Components

### Notebooks

The `notebooks/` directory contains Jupyter notebooks that walk through the core features of the project:

- **`01_single_agent_from_personal_data.ipynb`**: Explores creating a single LLM persona from personal data (like a CV) and testing its accuracy and consistency against the real person's answers. It compares personas generated from structured vs. unstructured data.

- **`02_synthetic_persona_generation.ipynb`**: Details the process of creating synthetic personas. It covers extracting structured profiles from real data, dealing with LLM biases in generation, and a "file-first" approach where data files are generated before the persona.

- **`03_building_a_fictional_neighbourhood.ipynb`**: Generates a fictional neighbourhood of 100 synthetic personas based on real-world census data for E8, London. It creates households, assigns demographics, and generates rich context statements for each persona.

### Web App & Experiments

The `web/` directory contains a SvelteKit application for interactive experiments and visualization of survey results.

- **`01-random-person-generator`**: This experiment generates random personas using an LLM and displays them on a map. It shows statistics on the generated population, highlighting the biases that can emerge from relying on LLMs for random data generation.

- **`02-testing-space-before-it-happens`**: This experiment simulates a real-world scenario where a community in Dalston, London, decides what to do with a collectively owned plot of land. It uses the 100 synthetic personas generated in the notebooks to survey them on their preferences, visualizes the results, and generates an AI image of the community's final vision.

To run the web app:
1. Start the Python API server: `uv run python -m centuria.api.server`
2. In another terminal, navigate to the `web` directory.
3. Install dependencies: `npm install`
4. Start the development server: `npm run dev`

### `src` Library

The `src/centuria/` directory contains the core Python library, providing modules for:
- `models`: Pydantic data models
- `llm`: LiteLLM client & prompts
- `persona`: Persona generation
- `survey`: Survey execution & analysis
- `data`: Data loading utilities

## Getting Started

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)**
2. **Clone the repository**
3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```
4. **Install dependencies:**
   ```bash
   uv sync
   ```
5. **Launch Jupyter Lab to explore the notebooks:**
   ```bash
   uv run jupyter lab
   ```

## License

MIT