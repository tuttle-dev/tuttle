# Tuttle – development & build tasks

set dotenv-load := false

repo     := justfile_directory()
electron := repo / "ui"
app      := electron / "release/mac-arm64/Tuttle.app"

# ── Development ─────────────────────────────────────────────────────────────

# Electron + Vite dev server (hot reload, live Python from .venv)
# vite-plugin-electron auto-launches Electron when Vite starts in dev mode.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    export TUTTLE_DATA_DIR="${TUTTLE_DATA_DIR:-$HOME/.tuttle-dev}"
    cd "{{electron}}"
    npm run build
    VITE_DEV_SERVER_URL=http://localhost:5173 npx vite

# ── Build ───────────────────────────────────────────────────────────────────

# Build the Python RPC core with PyInstaller
build-core:
    uv run --no-sync python -m PyInstaller --clean --noconfirm "{{repo}}/tuttle-rpc.spec"

# Smoke-test the frozen core: verify every RPC domain is bundled
smoke-core:
    uv run --no-sync python "{{repo}}/scripts/smoke_core.py"

# Build the Electron renderer (Vite + TypeScript)
build-renderer:
    cd "{{electron}}" && npm run build

# Remove previous packaged app to avoid launching stale builds
clean-app:
    rm -rf "{{electron}}/release"

# Package the Electron .app (requires build-core + build-renderer first)
pack target="dir":
    cd "{{electron}}" && CSC_IDENTITY_AUTO_DISCOVERY=false npx electron-builder --mac {{target}}
    @echo "Ad-hoc signing all binaries…"
    find "{{app}}" -type f \( -name '*.dylib' -o -name '*.so' -o -perm +111 \) -exec codesign --force --sign - {} \; 2>/dev/null || true
    codesign --force --deep --sign - "{{app}}"

# Full build: core → renderer → package (pass "dmg" for .dmg)
build target="dir": clean-app build-core smoke-core build-renderer (pack target)
    @echo "✓ {{electron}}/release/"

# Create a beta .zip with an install script that strips quarantine
beta: (build "dir")
    #!/usr/bin/env bash
    set -euo pipefail
    staging="{{electron}}/release/beta"
    rm -rf "$staging"
    mkdir -p "$staging"
    cp -R "{{app}}" "$staging/"
    cat > "$staging/Install Tuttle.command" << 'SCRIPT'
    #!/bin/bash
    set -e
    cd "$(dirname "$0")"
    dest="/Applications/Tuttle.app"
    [ -d "$dest" ] && rm -rf "$dest"
    cp -R "Tuttle.app" "$dest"
    xattr -cr "$dest"
    echo ""
    echo "✓ Tuttle installed to /Applications"
    echo "  You can now open it from Launchpad or Spotlight."
    echo ""
    read -n1 -rsp "Press any key to close…"
    SCRIPT
    chmod +x "$staging/Install Tuttle.command"
    cd "{{electron}}/release"
    zip -ry "Tuttle-beta.zip" beta/
    rm -rf "$staging"
    echo "✓ {{electron}}/release/Tuttle-beta.zip"

# ── Run ─────────────────────────────────────────────────────────────────────

# Launch the packaged Tuttle.app
run:
    @test -d "{{app}}" || (echo "No app found. Run 'just build' first." && exit 1)
    open "{{app}}"

# Build and run
br: build run

# ── Calendar helper (dev-mode workaround) ───────────────────────────────────

# Build the TuttleCalendar.app helper and request calendar access.
# This intentionally targets the real ~/.tuttle (not ~/.tuttle-dev):
# the helper's macOS calendar permission grant is tied to that fixed
# path, which is where the packaged app also looks for it.
calendar-setup:
    TUTTLE_DATA_DIR="$HOME/.tuttle" uv run --no-sync python -c "from tuttle.eventkit_bridge import _ensure_helper; _ensure_helper()"
    open --wait-apps ~/.tuttle/TuttleCalendar.app --args request-access
    @echo "Check System Settings → Privacy → Calendars for 'Tuttle Calendar'"

# ── Test ─────────────────────────────────────────────────────────────────────

# Run the full test suite (Python unit tests + TypeScript type-check)
test *args="":
    cd "{{electron}}" && npx tsc --noEmit
    uv run --no-sync python -m pytest {{args}}


# Create a new Alembic migration from the current SQLModel diff.
#   just migrate "add foo to client"
# Runs autogenerate against a throw-away temp DB and writes a new
# revision to tuttle/migrations/versions/. ALWAYS review the result —
# autogenerate misreads renames as drop+add (data loss).
migrate message:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -t tuttle_migrate.XXXXXX.db)
    trap 'rm -f "$tmp"' EXIT
    TUTTLE_DB_URL="sqlite:///$tmp" uv run --no-sync alembic upgrade head
    TUTTLE_DB_URL="sqlite:///$tmp" uv run --no-sync alembic revision --autogenerate -m "{{message}}"
    echo ""
    echo "✓ Revision written. REVIEW it before committing:"
    echo "  - any op.drop_column + op.add_column pair is a rename → use op.alter_column(new_column_name=...)"
    echo "  - no \`from tuttle.model import ...\`"
    echo "  - PRAGMA foreign_key_check after batch ops on FK tables"

# Refresh the document translation catalogs (tuttle/locales) from the code and templates.
i18n:
    #!/usr/bin/env bash
    set -euo pipefail
    pot=$(mktemp -t tuttle_messages.XXXXXX.pot)
    trap 'rm -f "$pot"' EXIT
    uv run --no-sync pybabel -q extract --ignore-dirs=".* node_modules" -F "{{repo}}/babel.cfg" -o "$pot" --no-location --add-comments=Translators: --project=Tuttle --copyright-holder="Tuttle contributors" --msgid-bugs-address=https://github.com/tuttle-dev/tuttle/issues "{{repo}}"
    uv run --no-sync pybabel update -i "$pot" -d "{{repo}}/tuttle/locales" --ignore-pot-creation-date --ignore-obsolete

# Start the catalog for a new document language, e.g. `just i18n-add fr`.
i18n-add lang:
    #!/usr/bin/env bash
    set -euo pipefail
    pot=$(mktemp -t tuttle_messages.XXXXXX.pot)
    trap 'rm -f "$pot"' EXIT
    uv run --no-sync pybabel -q extract --ignore-dirs=".* node_modules" -F "{{repo}}/babel.cfg" -o "$pot" --no-location --add-comments=Translators: --project=Tuttle --copyright-holder="Tuttle contributors" --msgid-bugs-address=https://github.com/tuttle-dev/tuttle/issues "{{repo}}"
    uv run --no-sync pybabel init -i "$pot" -d "{{repo}}/tuttle/locales" -l "{{lang}}"


# Fail if tuttle/model.py and tuttle/migrations/versions/ disagree.
# Wire this into CI to prevent silent schema drift.
check-migrations:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -t tuttle_check.XXXXXX.db)
    trap 'rm -f "$tmp"' EXIT
    TUTTLE_DB_URL="sqlite:///$tmp" uv run --no-sync alembic upgrade head
    TUTTLE_DB_URL="sqlite:///$tmp" uv run --no-sync alembic check

# Capture a single view screenshot: just screenshot <sidebar-id> <output-path>
screenshot view out="": build-renderer
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{electron}}"
    npx --yes tsx scripts/capture-view.ts {{view}} {{out}}

# Capture all README screenshots with macOS-style framing
screenshots: build-renderer
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{electron}}"
    pairs="dashboard:screenshot-dashboard timetracking:screenshot-timetracking invoicing:screenshot-invoices tax:screenshot-tax salary:screenshot-salary import:screenshot-import"
    for pair in $pairs; do
        view="${pair%%:*}"
        file="${pair##*:}"
        echo "── Capturing $view ──"
        npx --yes tsx scripts/capture-view.ts "$view" "../assets/images/${file}.png"
    done
    echo "✓ All screenshots captured"

# ── Utilities ───────────────────────────────────────────────────────────────

# Install/sync Python dependencies
deps:
    uv sync

# Install Node dependencies
deps-node:
    cd "{{electron}}" && npm ci

# Install all dependencies
deps-all: deps deps-node

# Nothing else moves the lockfiles: `uv sync`, `uv lock` and `npm ci` all keep
# the locked versions. This rewrites uv.lock and ui/package-lock.json and
# installs the result, to try an upgrade locally; run `just test` afterwards.
# `just upgrade-pr` opens the pull request instead, without installing anything.
#
# Upgrade every dependency to the newest version its declared range allows
upgrade:
    uv lock --upgrade
    uv sync
    cd "{{electron}}" && npm update

# `just release` runs this after every release, so each upgrade is tested by
# the usual checks and used in development for a whole cycle before it ships.
# Upgrading inside the release itself would tag versions no test has seen. Run
# it by hand to get a fix out before the next release.
#
# Works in a temporary worktree of origin/main: this checkout, its branch and
# the installed packages stay as they are. The branch `upgrade-dependencies` is
# rebuilt on every run, so a pull request still open is refreshed instead of a
# second one appearing.
#
# Open a pull request that upgrades uv.lock and ui/package-lock.json
upgrade-pr:
    #!/usr/bin/env bash
    set -euo pipefail
    branch="upgrade-dependencies"
    git fetch --quiet origin main
    work=$(mktemp -d)
    trap 'git worktree remove --force "$work/tree" 2>/dev/null || true; rm -rf "$work"' EXIT
    git worktree add --quiet --detach "$work/tree" origin/main
    cd "$work/tree"

    uv lock --upgrade 2>&1 | tee "$work/uv.log"
    cp ui/package-lock.json "$work/package-lock.before.json"
    # Lockfile only: nothing is installed, so no package script runs.
    (cd ui && npm update --package-lock-only --ignore-scripts)

    if git diff --quiet -- uv.lock ui/package-lock.json; then
        echo "✓ Both lockfiles are up to date. No pull request needed."
        exit 0
    fi

    python_changes=$(grep -E '^(Updated|Added|Removed) ' "$work/uv.log" | sed 's/^/- /' || true)
    ui_changes=$(node -e '
        const fs = require("fs");
        const [before, after, manifest] = process.argv.slice(1).map((f) => JSON.parse(fs.readFileSync(f, "utf8")));
        const names = Object.keys(Object.assign({}, manifest.dependencies, manifest.devDependencies)).sort();
        for (const name of names) {
            const key = "node_modules/" + name;
            const was = (before.packages[key] || {}).version;
            const now = (after.packages[key] || {}).version;
            if (was !== now) console.log("- " + name + " " + was + " → " + now);
        }
    ' "$work/package-lock.before.json" ui/package-lock.json ui/package.json)
    if git diff --quiet -- ui/package-lock.json; then
        ui_changes="No changes."
    elif [[ -z "$ui_changes" ]]; then
        ui_changes="Only transitive dependencies changed."
    fi
    {
        echo "Upgrade of both lockfiles to the newest versions the declared ranges allow, opened by \`just upgrade-pr\`. \`just release\` runs it after every release, so the upgrade is tested and used for a whole cycle before it ships."
        echo
        echo "The checks on this pull request test the result. Packaging is not built here: the core smoke test runs in the merge queue, and Pack Electron App runs on \`main\`."
        echo
        echo "**Python** (\`uv.lock\`)"
        echo
        echo "${python_changes:-No changes.}"
        echo
        echo "**UI** (\`ui/package-lock.json\`), direct dependencies"
        echo
        echo "$ui_changes"
    } > "$work/body.md"

    git commit --quiet -m "Upgrade dependencies" -- uv.lock ui/package-lock.json
    git push --quiet --force origin "HEAD:refs/heads/$branch"
    open=$(gh pr list --head "$branch" --state open --json number --jq '.[0].number // empty')
    if [[ -n "$open" ]]; then
        gh pr edit "$open" --body-file "$work/body.md"
        echo "✓ Refreshed the open dependency upgrade pull request."
    else
        gh pr create --base main --head "$branch" --title "Upgrade dependencies" --body-file "$work/body.md"
    fi

# Install the pre-commit hooks (run once after cloning)
precommit:
    uv run --no-sync pre-commit install

# Reset the demo user data
demo-reset:
    uv run --no-sync python -c "from tuttle.app.demo.intent import DemoIntent; DemoIntent().reset(); print('Demo user reset')"

# Wipe the dev data directory and start fresh
reset:
    rm -rf "${TUTTLE_DATA_DIR:-$HOME/.tuttle-dev}"
    @echo "✓ Dev data removed – next 'just dev' will recreate everything from scratch"

# Copy production databases into the dev data directory for testing on real data.
# One-way: dev will auto-migrate the copies on next launch.
sync-data:
    #!/usr/bin/env bash
    set -euo pipefail
    src="$HOME/.tuttle"
    dst="${TUTTLE_DATA_DIR:-$HOME/.tuttle-dev}"
    if [[ "$src" == "$dst" ]]; then echo "Error: source and destination are the same"; exit 1; fi
    if [[ ! -d "$src" ]]; then echo "No production data at $src"; exit 1; fi
    mkdir -p "$dst"
    cp "$src"/app.db "$dst"/ 2>/dev/null || true
    for f in "$src"/*.db; do
        [[ -e "$f" ]] && cp "$f" "$dst"/
    done
    echo "✓ Copied production databases to $dst"
    echo "  Next 'just dev' will auto-migrate them to the current dev schema."

# ── Release ─────────────────────────────────────────────────────────────────

# Bump version, commit, tag, push to origin, create GitHub release.
#
# bumpversion also rewrites the download links in index.html (the GitHub Pages
# landing page) to the asset filenames of the new version — see
# [tool.bumpversion.files] in pyproject.toml. Those files only exist once the
# pack-electron workflow finishes; until then the page falls back to the release
# page via the GitHub API.
#
#   just release patch                  3.1.0 → 3.1.1
#   just release minor                  3.1.0 → 3.2.0
#   just release major                  3.1.0 → 4.0.0
#   just release minor --pre a          3.1.0 → 3.2.0a1   (alpha)
#   just release patch --pre rc         3.1.0 → 3.1.1rc1  (release candidate)
#
# Add --dry-run to preview without changing anything.
#
# Afterwards opens the dependency upgrade pull request for the next release
# (`just upgrade-pr`).
#
# Runs only on main, and only when main has everything origin/main has: the
# version bump is committed and tagged locally before the push, so a release
# from the wrong branch or a stale main leaves a tag behind that blocks the next try.
release part *flags="":
    #!/usr/bin/env bash
    set -euo pipefail
    branch=$(git branch --show-current)
    if [[ "$branch" != "main" ]]; then
        echo "Releases are made from main, but you are on '${branch:-a detached HEAD}'." >&2
        echo "Run: git switch main && git pull" >&2
        exit 1
    fi
    git fetch --quiet origin main
    if ! git merge-base --is-ancestor origin/main HEAD; then
        echo "Your main is missing commits from origin/main." >&2
        echo "Run: git pull" >&2
        exit 1
    fi
    dry_run=0
    pre=""
    bump_flags=()
    for arg in {{flags}}; do
        if [[ "$arg" == "--pre" ]]; then pre="next"; continue; fi
        if [[ "$pre" == "next" ]]; then pre="$arg"; continue; fi
        if [[ "$arg" == "--dry-run" ]]; then dry_run=1; fi
        bump_flags+=("$arg")
    done
    if [[ -n "$pre" && "$pre" != "next" ]]; then
        base=$(uv run --no-sync python -m bumpversion show new_version --increment {{part}})
        bump_flags+=(--new-version "${base}${pre}1")
    fi
    # uv.lock is re-locked and staged by bumpversion's pre_commit_hooks (see
    # pyproject.toml) so it lands in the bump commit. Staging it here instead
    # would leave a staged change that bumpversion rejects as a dirty tree.
    uv run --no-sync python -m bumpversion bump {{part}} ${bump_flags[@]+"${bump_flags[@]}"}
    if [[ "$dry_run" -eq 1 ]]; then exit 0; fi
    tag=$(git describe --tags --abbrev=0)
    version="${tag#v}"
    git push origin main
    git push origin "$tag"

    # Build release body: download guide + auto-generated changelog
    notes=$(gh api repos/{owner}/{repo}/releases/generate-notes \
        -f tag_name="$tag" --jq .body 2>/dev/null || true)
    notes_file=$(mktemp)
    trap 'rm -f "$notes_file"' EXIT
    sed "s/__VERSION__/${version}/g" .github/release-body-template.md > "$notes_file"
    printf '\n%s\n' "$notes" >> "$notes_file"

    gh_flags=(--notes-file "$notes_file")
    if [[ "$tag" == *a* || "$tag" == *b* || "$tag" == *rc* ]]; then
        gh_flags+=(--prerelease)
    fi
    gh release create "$tag" "${gh_flags[@]}"

    # Start the dependency upgrade for the next release (see `upgrade-pr`). The
    # release is out by now, so a failure here must not look like a failed release.
    if ! "{{just_executable()}}" --justfile "{{justfile()}}" upgrade-pr; then
        echo "The release is published, but the dependency upgrade pull request could not be opened." >&2
        echo "Run: just upgrade-pr" >&2
    fi
