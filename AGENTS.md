# Agent Instructions

## Schema changes

Schema lives in `tuttle/model.py`. Migrations are Alembic in `tuttle/migrations/`.
Any change to a SQLModel class requires `just migrate "<msg>"` + reviewing the
generated revision for rename-as-drop+add traps. See
`.cursor/rules/schema-migrations.mdc` and `tuttle/migrations/README.md`.

## Verification

For big new features, add a new contract and project to the Harry tuttle user for demonstration purposes.

### UI verification playbook

UI verification is useful when a change affects the Electron shell, navigation, forms,
rendered invoice/timesheet flows, or any visible product copy. It should complement,
not replace, unit tests and human UX review.

#### When to run UI verification

- Run an Electron UI smoke when the PR changes a user-visible screen, route,
  modal, keyboard shortcut, import/export interaction, or platform packaging.
- Prefer a narrow path that exercises the changed surface instead of clicking the
  whole app. Example: launch the app, open the affected screen, perform the one
  edited action, and capture the before/after state.
- For non-UI changes, state that no UI surface changed rather than spending tokens
  on screenshots that do not prove the patch.

#### How to run it

- Use Playwright Electron where practical: <https://playwright.dev/docs/api/class-electron>.
- If Playwright setup is heavier than the change justifies, use the existing app
  start command plus manual/agent-driven clicks and document the exact path.
- Keep fixtures local and synthetic. Do not use real customer names, invoices,
  email addresses, API keys, or private business data in screenshots.

#### Evidence to include

- Screenshots or a short recording for every PR that changes product UI.
- The command used to start the app and the exact navigation path tested.
- Any known limitation, such as a screen that still needs final human review or a
  platform-specific path that was not exercised locally.

#### When not to over-test

- Documentation-only, schema-only, and backend-only PRs do not need Electron
  screenshots unless they also affect visible UI behavior.
- Do not attempt broad exploratory clicking for small patches. Prefer one focused
  UI smoke that proves the changed behavior and leaves final UX judgment to a
  human reviewer.
