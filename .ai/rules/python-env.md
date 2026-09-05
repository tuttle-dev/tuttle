# Python Environment

This project uses **uv** for dependency management. The virtualenv lives at `.venv/`.

```bash
# Run Python via uv
uv run pytest ...
uv run python -c "..."

# Or use just (which uses uv internally)
just test

# NEVER use system python, miniforge, or direct .venv paths
# python -m pytest ...
# .venv/bin/python -m pytest ...
```
