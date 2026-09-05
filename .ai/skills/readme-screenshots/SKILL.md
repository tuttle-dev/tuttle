# README Screenshots

Take screenshots of Tuttle app views for the README. Use when updating,
refreshing, or regenerating README screenshots.

## Steps

1. Read `README.md` and find every `<img>` tag referencing `screenshot-*.png`.
2. For each screenshot, determine which app view it depicts from context
   (the heading, surrounding text, and filename).
3. Decide whether the screenshot needs updating (new view, changed UI, missing file).
4. For each view that needs a screenshot, call the capture helper.

## Capture helper

`ui/scripts/capture-view.ts` launches the Electron app, navigates to a single
view, and saves a screenshot. It manages the demo user automatically.

```bash
cd ui && npx tsx scripts/capture-view.ts <sidebar-id> <output-path>
```

**Sidebar IDs** (match `Sidebar.tsx` SECTIONS):

| ID             | Label           |
|----------------|-----------------|
| `dashboard`    | Dashboard       |
| `timeline`     | Timeline        |
| `tax`          | Tax & Reserves  |
| `salary`       | Salary          |
| `import`       | Import          |
| `timetracking` | Time Tracking   |
| `invoicing`    | Invoicing       |
| `projects`     | Projects        |
| `contracts`    | Contracts       |
| `clients`      | Clients         |
| `contacts`     | Contacts        |

Example:

```bash
cd ui && npx tsx scripts/capture-view.ts dashboard ../assets/images/screenshot-dashboard.png
```

## Decision guidelines

- A screenshot named `screenshot-invoices.png` maps to sidebar ID `invoicing`.
- If the README mentions a view in a `### Feature` section but has no screenshot,
  suggest adding one.
- If a screenshot file exists but the README no longer references it, flag it
  as potentially stale.
- Capture only views the user asks for, or all README-referenced views if
  the user says "update all screenshots".

## Prerequisites

First-time setup (once):

```bash
cd ui && npm install --save-dev playwright tsx && npx playwright install chromium
```
