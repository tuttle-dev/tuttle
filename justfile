# Tuttle – development & build tasks

set dotenv-load := false

repo     := justfile_directory()
electron := repo / "ui"
venv     := repo / ".venv"
python   := venv / "bin/python"
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
    {{python}} -m PyInstaller --clean --noconfirm {{repo}}/tuttle-rpc.spec

# Smoke-test the frozen core: verify every RPC domain is bundled
smoke-core:
    {{python}} {{repo}}/scripts/smoke_core.py

# Build the Electron renderer (Vite + TypeScript)
build-renderer:
    cd {{electron}} && npm run build

# Remove previous packaged app to avoid launching stale builds
clean-app:
    rm -rf "{{electron}}/release"

# Package the Electron .app (requires build-core + build-renderer first)
pack target="dir":
    cd {{electron}} && CSC_IDENTITY_AUTO_DISCOVERY=false npx electron-builder --mac {{target}}
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

# Build the TuttleCalendar.app helper and request calendar access
calendar-setup:
    {{python}} -c "from tuttle.eventkit_bridge import _ensure_helper; _ensure_helper()"
    open --wait-apps ~/.tuttle/TuttleCalendar.app --args request-access
    @echo "Check System Settings → Privacy → Calendars for 'Tuttle Calendar'"

# ── Test ─────────────────────────────────────────────────────────────────────

# Run the test suite
test *args="":
    {{python}} -m pytest {{args}}


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
    TUTTLE_DB_URL="sqlite:///$tmp" {{venv}}/bin/alembic upgrade head
    TUTTLE_DB_URL="sqlite:///$tmp" {{venv}}/bin/alembic revision --autogenerate -m "{{message}}"
    echo ""
    echo "✓ Revision written. REVIEW it before committing:"
    echo "  - any op.drop_column + op.add_column pair is a rename → use op.alter_column(new_column_name=...)"
    echo "  - no \`from tuttle.model import ...\`"
    echo "  - PRAGMA foreign_key_check after batch ops on FK tables"


# Fail if tuttle/model.py and tuttle/migrations/versions/ disagree.
# Wire this into CI to prevent silent schema drift.
check-migrations:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -t tuttle_check.XXXXXX.db)
    trap 'rm -f "$tmp"' EXIT
    TUTTLE_DB_URL="sqlite:///$tmp" {{venv}}/bin/alembic upgrade head
    TUTTLE_DB_URL="sqlite:///$tmp" {{venv}}/bin/alembic check

# Capture a single view screenshot: just screenshot <sidebar-id> <output-path>
screenshot view out="": build-renderer
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{electron}}"
    npx --yes tsx scripts/capture-view.ts {{view}} {{out}}

# ── Utilities ───────────────────────────────────────────────────────────────

# Install/sync Python dependencies
deps:
    uv sync

# Install Node dependencies
deps-node:
    cd {{electron}} && npm ci

# Install all dependencies
deps-all: deps deps-node

# Install the pre-commit hooks (run once after cloning)
precommit:
    {{venv}}/bin/pre-commit install

# Reset the demo user data
demo-reset:
    {{python}} -c "from tuttle.app.demo.intent import DemoIntent; DemoIntent().reset(); print('Demo user reset')"

# Wipe all production app data and start fresh
reset:
    rm -rf ~/.tuttle
    @echo "✓ ~/.tuttle removed – next launch will recreate everything from scratch"

# Wipe the dev data directory
reset-dev:
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
#   just release patch                  3.1.0 → 3.1.1
#   just release minor                  3.1.0 → 3.2.0
#   just release major                  3.1.0 → 4.0.0
#   just release minor --pre a          3.1.0 → 3.2.0a1   (alpha)
#   just release patch --pre rc         3.1.0 → 3.1.1rc1  (release candidate)
#
# Add --dry-run to preview without changing anything.
release part *flags="":
    #!/usr/bin/env bash
    set -euo pipefail
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
        base=$({{python}} -m bumpversion show new_version --increment {{part}})
        bump_flags+=(--new-version "${base}${pre}1")
    fi
    {{python}} -m bumpversion bump {{part}} ${bump_flags[@]+"${bump_flags[@]}"}
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
