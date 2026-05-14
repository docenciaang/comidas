# Repository Guidelines

## Project Structure & Module Organization

The repository root is `menu_familiar/`. Application code lives in `app/`.

- `app/main.py`: Typer CLI entrypoint.
- `app/api.py`: FastAPI application.
- `app/web/`: integrated web router, Jinja templates, and static assets.
- `app/core/`: business logic (`menu_manager.py`, `recipes.py`, `shopping.py`, `family.py`).
- `app/ai/`: AI agent, assistant, and prompt templates.
- `app/mcp/`: local MCP-facing server, tools, and resources.
- `app/models/`: SQLModel entities and DB/config helpers.
- `app/services/`: external integrations such as notifications.
- `data/`: SQLite DB and cache files.
- `docs/`: architecture and project documentation.

Tests are not present yet; add them under `tests/` at the repository root.

## Build, Test, and Development Commands

Run commands from `menu_familiar/` unless using `uv --directory`.

- `uv venv && source .venv/bin/activate`: create and activate the virtualenv.
- `uv pip install -r requirements.txt`: install dependencies.
- `uv run -m app.main init-db`: create the SQLite schema.
- `uv run -m app.main seed-demo`: load demo family members and recipes.
- `uv run -m app.main week`: print the current weekly menu.
- `uv run -m app.main serve-api`: start API and integrated web UI using `host` and `port` from `config.yaml`.
- `python3 -m py_compile app/**/*.py`: quick syntax check before submitting changes.

## Coding Style & Naming Conventions

Use Python 3.11+ and 4-space indentation. Prefer small, focused modules and explicit imports.

- Files and modules: `snake_case.py`
- Classes: `PascalCase`
- Functions, variables, CLI commands: `snake_case`
- Keep comments short and only where logic is not obvious.
- Default to ASCII unless a file already requires Unicode.

No formatter or linter is configured yet. Follow existing style and keep diffs minimal.

## Testing Guidelines

Use `pytest` when adding tests. Name files `test_<module>.py` and place them in `tests/`.

- Prefer unit tests for `app/core/`, `app/ai/`, and `app/mcp/`.
- Add API tests for critical endpoints such as `/menus/week`, `/suggest`, and `/family`.
- Cover both happy-path and validation/error behavior.

## Commit & Pull Request Guidelines

Git history is not available in this scaffold, so use clear imperative commit messages such as `Add shopping list export`.

Pull requests should include:

- A short summary of the user-visible or architectural change.
- Notes on setup, migration, or config impact.
- Test evidence (`uv run ...`, `pytest`, or manual API checks).
- Screenshots only when UI output or docs rendering meaningfully changed.

## Security & Configuration Tips

Do not commit real secrets in `.env`. Keep API keys local and prefer mock mode unless real provider integration is required. Validate changes to `config.yaml` and avoid hardcoding credentials outside configuration files.
