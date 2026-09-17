# SME Ledger — Flask Web Application

A Flask web interface for the SME Ledger V2 financial intelligence system.

## Architecture

SMS/transaction text
    -> Gemma 3 270M GGUF
    -> structured JSON
    -> validation/normalization
    -> local ledger
    -> deterministic financial analytics
    -> Gemma interpretation
    -> dashboard/user guidance

The application is intentionally structured so the LLM does language understanding while
Python handles deterministic financial calculations.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Place the GGUF model in `models/` or set `MODEL_PATH` in `.env`.

## Planned modules

- `routes/` — HTTP/UI/API endpoints
- `services/` — model inference, extraction, analytics and validation
- `models/` — database models
- `templates/` — Jinja UI
- `static/` — CSS/JS/assets
- `tests/` — unit and integration tests
- `scripts/` — setup, model and data utilities
