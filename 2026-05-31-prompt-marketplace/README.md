# Prompt Marketplace

A minimal FastAPI service that lets users browse and submit AI prompts.

## Features
- List public prompts
- Submit a new prompt (requires API key)
- Simple SQLite storage via SQLModel
- OpenAPI docs automatically generated

## Quick start (local)
```bash
cd 2026-05-31-prompt-marketplace
python -m venv .venv
source .venv/bin/activate  # on Windows use .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```
