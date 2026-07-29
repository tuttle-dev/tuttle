# Agent Instructions

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
