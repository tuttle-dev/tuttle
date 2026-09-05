# Testing Workflow

## Always run tests after implementation

After making code changes, run the full unit test suite before finishing:

```bash
uv run pytest --tb=short -q
```

Do NOT skip this step. Fix any failures introduced by the changes.

## Adding tests for new features

Add tests sparingly but when needed. Not every change requires a new test, but new features and bug fixes that could regress should have coverage.
