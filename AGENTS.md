# Agent Instructions

<!-- lean-ctx -->
## lean-ctx

Prefer lean-ctx MCP tools over native equivalents for token savings.
Full rules: @LEAN-CTX.md
<!-- /lean-ctx -->

<!-- lean-ctx-compression -->
OUTPUT STYLE: dense
- Each statement = one atomic fact line
- Use abbreviations: fn, cfg, impl, deps, req, res, ctx, err, ret
- Diff lines only (+/-/~), never repeat unchanged code
- Symbols: → (causes), + (adds), − (removes), ~ (modifies), ∴ (therefore)
- No narration, no filler, no hedging
- BUDGET: ≤200 tokens per response unless code block required
<!-- /lean-ctx-compression -->

## Schema changes

Schema lives in `tuttle/model.py`. Migrations are Alembic in `tuttle/migrations/`.
Any change to a SQLModel class requires `just migrate "<msg>"` + reviewing the
generated revision for rename-as-drop+add traps. See
`.cursor/rules/schema-migrations.mdc` and `tuttle/migrations/README.md`.

## Verification

For big new features, add a new contract and project to the Harry tuttle user for demonstration purposes.

### UI
- Test UI changes using playwright electron. https://playwright.dev/docs/api/class-electron
- launch the electron app and provide screenshots as artefacts in PR comments to be reviewed.