# Code Flow Viz

A professional web app to visualize Python code as a data/control-flow graph.

- Backend: FastAPI (Python)
- Frontend: Static HTML/CSS/JS + Cytoscape.js
- Optional preprocessing via Gemini 2.5 Flash to strip comments/docstrings; local AST fallback is provided.

## Run locally

1. Python deps

```bash
cd /workspace/codeflowviz/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2. Environment (optional for Gemini)

```bash
export GOOGLE_API_KEY=YOUR_API_KEY
# or export GEMINI_API_KEY=YOUR_API_KEY
# export GEMINI_MODEL_NAME=gemini-2.5-flash
```

3. Start server

```bash
python -m app.main
```

The frontend is served at `http://localhost:8000/`.

## API

- POST `/api/preprocess` -> `{ clean_code, meta }`
- POST `/api/analyze` -> `{ clean_code, graph: { nodes, edges }, diagnostics, stats, meta }`

Request body:

```json
{ "code": "...python code...", "use_gemini": true }
```

## Notes

- If Gemini is not configured, the app will use an AST-based local preprocessor.
- The analyzer provides an approximate graph: variable definitions/uses, calls, loops, conditionals, functions, classes, and imports.
- Visualization is done with Cytoscape's `cose` layout. Adjust in `frontend/app.js` if preferred.