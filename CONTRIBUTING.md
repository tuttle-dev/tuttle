# Contributing

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

# Types of Contributions

## Report Bugs

Report bugs at <https://github.com/tuttle-dev/tuttle/issues>.

If you are reporting a bug, please include:

-   Your operating system name and version.
-   Any details about your local setup that might be helpful in
    troubleshooting.
-   Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

## Implement Features

Look through the GitHub issues for features. Anything tagged with
"enhancement" and "help wanted" is open to whoever wants to
implement it.

## Claiming Issues

When you're assigned to an issue, please open a draft PR within **7 days** to show progress. If no draft or open PR is submitted within that window, you will be un-assigned automatically so the issue is available for others. You can always request re-assignment if you need more time.

## Write Documentation

Tuttle could always use more documentation, whether as part of the
official docs, in docstrings, or even on the web in blog posts,
articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/tuttle-dev/tuttle/issues>.

If you are proposing a feature:

-   Explain in detail how it would work.
-   Keep the scope as narrow as possible, to make it easier to
    implement.
-   Remember that this is a volunteer-driven project, and that
    contributions are welcome :)

## AI-Assisted Contributions

AI tools are welcome for drafting code and documentation, but contributors remain fully responsible for all submitted changes. Pull requests consisting primarily of unreviewed or untested AI-generated content may be rejected.

Contributors using AI assistance are expected to:

-   Understand and be able to explain all submitted code during review
-   Verify that AI-generated suggestions are correct
-   Test changes locally before opening a pull request
-   Disclose significant AI assistance in the pull request description

# Pull Request Guidelines

## PR Template

When you open a pull request, your PR body will be pre-filled from the [PR template](/.github/PULL_REQUEST_TEMPLATE.md). It contains a **Summary** section and a **Checklist** of items to complete before requesting review. Please work through each checklist item — it covers testing, pre-commit hooks, documentation, schema migrations, and screenshots where applicable.

Outside contributors are required to keep the checklist in their PR body. Org members may omit it.

## CI Checks

Your PR must pass the following automated checks before it can be merged:

| Check | What it verifies |
|---|---|
| `build (3.x)` | The test suite passes on each supported Python version |
| `check-template` | PR body includes the Checklist section (outside contributors only) |
| `conflict-check` | The branch has no merge conflicts with `main` |

In addition, the following rules are enforced on the `main` branch:

-   **At least one approving review** is required (the maintainer can bypass this for their own PRs).
-   **Stale reviews are dismissed** when new commits are pushed — reviewers must re-approve after changes.
-   **All review conversations must be resolved** before merging.
-   **The branch must be up-to-date with `main`**. If your branch falls behind, rebase or merge `main` into it.

### Responding to review feedback

When changes are requested on your PR, please respond (by pushing updates or commenting) within:

-   **3 days** for issues labeled `priority: high`
-   **7 days** for all other issues

PRs without author follow-up within this window will be labeled `stale`.

# Get Started!

Ready to contribute? Here's how to set up Tuttle for local development.

## Prerequisites

-   Python (see `pyproject.toml` for the minimum version)
-   [uv](https://docs.astral.sh/uv/)
-   [just](https://github.com/casey/just) (task runner)
-   Node.js (see `ui/package.json` for the minimum version)

## Development Setup

1.  Fork the repo on GitHub.

2.  Clone your fork locally:

    ```shell
    git clone git@github.com:your_name_here/tuttle.git
    cd tuttle/
    ```

3.  Install all dependencies (Python + Node):

    ```shell
    just deps-all
    ```

4.  Install the pre-commit hooks:

    ```shell
    just precommit
    ```

5.  Create a branch for local development:

    ```shell
    git checkout -b name-of-your-bugfix-or-feature
    ```

6.  When you're done making changes, run the full test suite (Python tests + TypeScript type-check):

    ```shell
    just test
    ```

7.  Commit your changes and push your branch to GitHub:

    ```shell
    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature
    ```

8.  Submit a pull request through the GitHub website.

## Key `just` Commands

Run `just --list` to see all available tasks. Here are the most important ones:

| Command | Description |
|---|---|
| `just dev` | Start the Electron app in dev mode (hot reload) |
| `just test` | Run the full test suite (Python + TypeScript type-check) |
| `just deps-all` | Install/sync all dependencies (Python + Node) |
| `just precommit` | Install the pre-commit hooks |
| `just build` | Full production build (PyInstaller + Electron) |
| `just migrate "<msg>"` | Generate an Alembic migration from model changes |
| `just sync-data` | Copy production data into the dev directory for testing |
| `just reset` | Wipe the dev data directory and start fresh |

## Running the App

Start the Electron app in development mode. The Python RPC core is
spawned automatically:

```shell
just dev
```

### Dev vs production data

`just dev` stores data in `~/.tuttle-dev/` (via the `TUTTLE_DATA_DIR`
env var) so that development never touches your production database in
`~/.tuttle/`. To test with your real data, copy it once:

```shell
just sync-data   # one-way copy ~/.tuttle → ~/.tuttle-dev
```

The dev app will auto-migrate the copies to the current schema on next
launch. Use `just reset` to wipe the dev data directory.

# Tips

To run a subset of tests:

```shell
just test tuttle_tests/test_model.py
```

To run a specific test:

```shell
just test tuttle_tests/test_model.py::TestContract::test_valid_instantiation
```

# Architecture

Tuttle is a desktop application with a Python core and an Electron UI shell.

- **Python core** (`tuttle/`): Business logic, data models, invoicing, tax calculations, and a JSON-RPC server (`tuttle/rpc_server.py`) that exposes the core as a stdio service.
- **Electron shell** (`ui/`): React + TypeScript desktop UI that communicates with the Python core via JSON-RPC over stdio.

### Architecture Notes

**The View**

- builds UI,
- reacts to data changes (by updating the UI)
- listens for events and forwards them to the Intent

**The Intent**

- receives events
- if some data is affected by the event, figure out which data source corresponds to that data
- transforms the event data to the data format required by the data source
- transform returned data source data to the data format required by the UI
- else, no data is affected by the event, handle the event (often using a util class).
- an example of this is sending invoices by mail.

**The Model (a.k.a data layer)**

- defines the entity
- define the entity source (file, remote API, local database, in-memory cache, etc)
- if a relational database is used, define the entity's relationship to other entities
- maintain the integrity of that relation (conflict strategies for insert operations are defined here, and integrity errors are thrown here, for example)
- defines classes that manipulate this source (open, read, write, ....)


As you go outer in layers (the outmost layer is the UI, the innermost is the data layer), communication can occur downward across layers, and horizontally, BUT a layer cannot skip the layer directly below it. This is to say:

* Data sources can communicate with each other. Thus `ClientDatasource.delete_client` can call `ContractDatasource.get_contract` for example.

* Intents can communicate with each other, and with any data source. Thus `ClientIntent` can call `ContractIntent` or `ContractDatasource` for example.
The UI can communicate with any intent (though often the UI is tied to only a single intent, and the intent can instead call the "other" intent). But it cannot communicate with a data source -- this would violate the do-not-skip-layers rule.
An inner layer cannot have a dependency on the layer above it. Thus an intent cannot instantiate a UI class, and a data source cannot instantiate an Intent class.

![](assets/images/mvi-concept.png)
