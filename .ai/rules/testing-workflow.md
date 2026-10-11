# Testing Workflow

## Always run tests after implementation

After making code changes, run the full unit test suite before finishing:

```bash
uv run pytest --tb=short -q
```

Do NOT skip this step. Fix any failures introduced by the changes.

The suite runs in parallel (pytest-xdist). Add `-n0` to run serially, e.g. for pdb or a single quick test file.

## Adding tests for new features

Add tests sparingly but when needed. Not every change requires a new test, but new features and bug fixes that could regress should have coverage.

## PDFs in tests

Tests get a blank page instead of a real PDF (see `tuttle_tests/conftest.py`), because the PDF engine is slow. Mark tests that check PDF output with `@pytest.mark.real_pdf_engine`.
