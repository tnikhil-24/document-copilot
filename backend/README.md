# Backend

FastAPI service for Document Copilot. See [CLAUDE.md](CLAUDE.md) for conventions and [../docs/guides/backend-setup.md](../docs/guides/backend-setup.md) for first-time setup details.

## Setup

```bash
cd backend
uv sync
cp .env.example .env   # fill in Supabase + OpenAI credentials
```

## Run the server

```bash
uv run uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Tests

```bash
uv run pytest -m "not integration"   # fast suite — no network/DB, must stay green
uv run pytest                        # full suite — needs live Supabase/OpenAI credentials
```

## Lint & format

```bash
uv run ruff check .
uv run ruff format .
```

## Database migrations (Alembic)

```bash
uv run alembic revision --autogenerate -m "description"   # after changing SQLAlchemy models — review before applying
uv run alembic upgrade head                               # apply to Supabase Postgres
```

## Managing dependencies

```bash
uv add <package>          # runtime dependency
uv add --dev <package>    # dev-only dependency (lint, test)
uv sync                   # install/update from the lockfile
```

Check [CLAUDE.md](CLAUDE.md) for the dependency policy before adding anything new.
