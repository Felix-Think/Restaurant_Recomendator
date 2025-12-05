Restaurant Recommendation (FastAPI)
===================================

This project uses uv for Python packaging and running the app.

Install uv
----------
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Set up and install deps
-----------------------
1) Create venv: `uv venv`
2) Activate:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
3) Install: `uv sync`
4) Export secrets (example):
   - `export OPENAI_API_KEY=...`
   - `export MONGODB_URI=mongodb+srv://...` (defaults to `mongodb://localhost:27017`)
   - `export MONGODB_DB=restaurant_recommendation`

Run the app with uv
-------------------
- Create Chroma DB (optional, for semantic retrieval): `uv run python utils/chroma_ingest.py`
- API/UI server: `uv run uvicorn web.app:app --reload --host 0.0.0.0 --port 8000`

Notes
-----
- Python 3.12+ required (per pyproject.toml).
- If you add dependencies, update `pyproject.toml` and run `uv sync` again.
