#!/usr/bin/env bash
# sync_ics.sh - Sync ICS toolkit from standalone repo into monorepo
#
# Usage:
#   ./scripts/sync_ics.sh          # sync from GitHub remote
#   ./scripts/sync_ics.sh --dry    # show what would change without writing
#
# Prerequisites:
#   git remote add ics-upstream https://github.com/JG-CSI-Velocity/ics_toolkit.git
#
# What gets synced:
#   ics_toolkit/        -> packages/ics_toolkit/src/ics_toolkit/  (source code)
#   tests/              -> tests/ics/                              (test files)
#   templates/          -> packages/ics_toolkit/src/ics_toolkit/templates/  (PPTX template)
#
# What is preserved (monorepo-only files):
#   packages/ics_toolkit/src/ics_toolkit/runner.py   (shared-context bridge)
#   packages/ics_toolkit/pyproject.toml              (monorepo package config)
#   tests/ics/test_runner.py                         (monorepo runner tests)

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
    echo "Run: git remote add $REMOTE https://github.com/JG-CSI-Velocity/ics_toolkit.git"
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

# --- Sync source code ---
echo "[1/3] Syncing source: ics_toolkit/ -> $SRC_PKG/"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- ics_toolkit/ | tar -t | sed 's|^ics_toolkit/||' | grep -v '^$' | sed 's/^/    /'
else
    # Back up monorepo-only files
    RUNNER_BACKUP=""
    if [[ -f "$SRC_PKG/runner.py" ]]; then
        RUNNER_BACKUP=$(mktemp)
        cp "$SRC_PKG/runner.py" "$RUNNER_BACKUP"
    fi

    # Extract source files (strip ics_toolkit/ prefix)
    git archive "$REMOTE/$BRANCH" -- ics_toolkit/ | tar -x --strip-components=1 -C "$SRC_PKG/"

    # Restore monorepo-only files
    if [[ -n "$RUNNER_BACKUP" ]]; then
        cp "$RUNNER_BACKUP" "$SRC_PKG/runner.py"
        rm "$RUNNER_BACKUP"
    fi

    echo "  Done."
fi
echo

# --- Sync tests ---
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

# --- Sync templates ---
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
    echo "  Review changes:"
    echo "    git diff --stat"
    echo "    git diff $SRC_PKG/"
    echo
    echo "  If everything looks good:"
    echo "    git add $SRC_PKG/ $TEST_DIR/"
    echo "    git commit -m 'chore(ics): sync from ics_toolkit upstream ${UPSTREAM_SHA:0:10}'"
fi
echo "=========================================="
