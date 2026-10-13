# User data stays private

Tuttle holds people's real business data: clients, rates, amounts, hours, invoice numbers and calendar entries. Treat anything the user shares from their own app (screenshots, logs, error messages, app output) as their real data, unless you produced it yourself from the demo user.

None of it may reach a public place: PR and issue titles, descriptions and comments, commit messages, code comments, tests and fixtures, docs, the README, or screenshots. Talking about it with the user in the session is fine.

- Describe a bug by how it happens, not by the user's numbers.
- Where an example needs figures, invent them or take them from the demo user, Harry Tuttle (`tuttle/demo.py`).
- Before running `gh pr create`, `gh pr edit`, `gh issue`, `git commit` or `git push`, reread the text for amounts, names, hours and dates that came from the user.
- Capture screenshots with `TUTTLE_DATA_DIR` set to a scratch directory that holds only demo data.
- If something leaks, remove it at once and tell the user where it appeared. GitHub keeps every revision of a PR or issue description, and only the web UI can delete one: click "edited", pick the revision, then "Delete revision from history".

```text
# BAD: the user's figures in a PR description
October showed €1,234 Planned on the dashboard but €56 in the tax view.

# GOOD: how it happens, no figures
The tax view counted only future calendar events as Planned; the dashboard also counted tracked work not yet invoiced.
```

Applies to everything published outside the user's machine.
