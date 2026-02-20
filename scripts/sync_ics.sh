#!/usr/bin/env bash
# ============================================================================
# sync_ics.sh -- Sync ICS Toolkit from standalone repo into the monorepo
# ============================================================================
#
# WHAT THIS DOES
# --------------
# Pulls the latest ICS toolkit code from the standalone GitHub repo
# (JG-CSI-Velocity/ics_toolkit) and copies it into the right spots
# in the analysis-platform monorepo. Use this after you've been working
# in the standalone ics_toolkit repo (Jupyter, testing, etc.) and want
# to bring those changes into the monorepo.
#
# HOW IT WORKS
# ------------
# 1. Fetches latest code from the "ics-upstream" git remote
# 2. Extracts source files:  ics_toolkit/  ->  packages/ics_toolkit/src/ics_toolkit/
# 3. Extracts test files:    tests/        ->  tests/ics/
# 4. Extracts templates:     templates/    ->  packages/ics_toolkit/src/ics_toolkit/templates/
# 5. Preserves monorepo-only files (runner.py, test_runner.py) by backing
#    them up before sync and restoring after
#
# FIRST-TIME SETUP (run once)
# ---------------------------
# cd analysis-platform
# git remote add ics-upstream https://github.com/JG-CSI-Velocity/ics_toolkit.git
#
# USAGE
# -----
# ./scripts/sync_ics.sh          Sync latest code (modifies files)
# ./scripts/sync_ics.sh --dry    Preview what would change (no modifications)
#
# AFTER RUNNING
# -------------
# 1. Review changes:     git diff --stat
# 2. Run tests:          uv run pytest tests/ics/ -q
# 3. Fix lint:           uv run ruff check packages/ics_toolkit/ tests/ics/ --fix
# 4. Check for stale imports -- the standalone repo uses "from tests.analysis..."
#    but the monorepo needs "from tests.ics.analysis..." (grep for "from tests."
#    in tests/ics/ and fix any that don't start with "from tests.ics.")
# 5. Stage and commit:   git add packages/ics_toolkit/src/ics_toolkit/ tests/ics/
#                         git commit -m "chore(ics): sync from upstream"
#
# FILES PRESERVED (not overwritten by sync)
# -----------------------------------------
# packages/ics_toolkit/src/ics_toolkit/runner.py   -- bridge to shared context
# packages/ics_toolkit/pyproject.toml              -- monorepo package config
# tests/ics/test_runner.py                         -- monorepo runner tests
#
# ============================================================================

set -euo pipefail

REMOTE="ics-upstream"
BRANCH="main"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PKG="packages/ics_toolkit/src/ics_toolkit"
TEST_DIR="tests/ics"

cd "$REPO_ROOT"

# Check remote exists
if ! git remote | grep -q "^${REMOTE}$"; then
    echo "ERROR: Remote '$REMOTE' not found."
    echo ""
    echo "First-time setup -- run this once:"
    echo "  git remote add $REMOTE https://github.com/JG-CSI-Velocity/ics_toolkit.git"
    exit 1
fi

DRY_RUN=false
if [[ "${1:-}" == "--dry" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN (no files will be modified) ==="
    echo
fi

echo "Fetching latest from $REMOTE/$BRANCH..."
git fetch "$REMOTE" "$BRANCH" --quiet

UPSTREAM_SHA=$(git rev-parse "$REMOTE/$BRANCH")
echo "Upstream commit: ${UPSTREAM_SHA:0:10}"
echo

# --- Step 1: Sync source code ---
echo "[1/3] Syncing source: ics_toolkit/ -> $SRC_PKG/"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- ics_toolkit/ | tar -t | sed 's|^ics_toolkit/||' | grep -v '^$' | sed 's/^/    /'
else
    # Back up monorepo-only files before overwriting
    RUNNER_BACKUP=""
    if [[ -f "$SRC_PKG/runner.py" ]]; then
        RUNNER_BACKUP=$(mktemp)
        cp "$SRC_PKG/runner.py" "$RUNNER_BACKUP"
    fi

    # Extract source files (strip ics_toolkit/ prefix so files land in the right place)
    git archive "$REMOTE/$BRANCH" -- ics_toolkit/ | tar -x --strip-components=1 -C "$SRC_PKG/"

    # Restore monorepo-only files
    if [[ -n "$RUNNER_BACKUP" ]]; then
        cp "$RUNNER_BACKUP" "$SRC_PKG/runner.py"
        rm "$RUNNER_BACKUP"
    fi

    echo "  Done."
fi
echo

# --- Step 2: Sync tests ---
echo "[2/3] Syncing tests: tests/ -> $TEST_DIR/"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- tests/ | tar -t | sed 's|^tests/||' | grep -v '^$' | sed 's/^/    /'
else
    # Back up monorepo-only test files
    RUNNER_TEST_BACKUP=""
    if [[ -f "$TEST_DIR/test_runner.py" ]]; then
        RUNNER_TEST_BACKUP=$(mktemp)
        cp "$TEST_DIR/test_runner.py" "$RUNNER_TEST_BACKUP"
    fi

    # Extract test files (strip tests/ prefix)
    git archive "$REMOTE/$BRANCH" -- tests/ | tar -x --strip-components=1 -C "$TEST_DIR/"

    # Restore monorepo-only test files
    if [[ -n "$RUNNER_TEST_BACKUP" ]]; then
        cp "$RUNNER_TEST_BACKUP" "$TEST_DIR/test_runner.py"
        rm "$RUNNER_TEST_BACKUP"
    fi

    echo "  Done."
fi
echo

# --- Step 3: Sync templates ---
echo "[3/3] Syncing templates: templates/ -> $SRC_PKG/templates/"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- templates/ | tar -t | sed 's|^templates/||' | grep -v '^$' | sed 's/^/    /'
else
    mkdir -p "$SRC_PKG/templates"
    git archive "$REMOTE/$BRANCH" -- templates/ | tar -x --strip-components=1 -C "$SRC_PKG/templates/"
    echo "  Done."
fi
echo

# --- Summary ---
echo "=========================================="
if $DRY_RUN; then
    echo "  DRY RUN complete. No files were changed."
else
    echo "  Sync complete from $REMOTE/$BRANCH"
    echo
    echo "  Next steps:"
    echo "    1. Review:  git diff --stat"
    echo "    2. Test:    uv run pytest tests/ics/ -q"
    echo "    3. Lint:    uv run ruff check packages/ics_toolkit/ tests/ics/ --fix"
    echo "    4. Check:   grep -r 'from tests\\.' tests/ics/ | grep -v 'from tests.ics'"
    echo "       (fix any bare 'from tests.' imports -> 'from tests.ics.')"
    echo "    5. Commit:  git add $SRC_PKG/ $TEST_DIR/"
    echo "                git commit -m 'chore(ics): sync from ics_toolkit upstream ${UPSTREAM_SHA:0:10}'"
fi
echo "=========================================="
