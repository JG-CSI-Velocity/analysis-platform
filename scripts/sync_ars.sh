#!/usr/bin/env bash
# ============================================================================
# sync_ars.sh -- Sync ARS Pipeline from standalone repo into the monorepo
# ============================================================================
#
# WHAT THIS DOES
# --------------
# Pulls the latest ARS pipeline code from the standalone GitHub repo
# (JG-CSI-Velocity/ars-pipeline) and copies it into the right spots
# in the analysis-platform monorepo. Use this after you've been working
# in the standalone ars-pipeline repo and want to bring those changes
# into the monorepo.
#
# IMPORTANT: The standalone package is named "ars" but the monorepo
# package is named "ars_analysis". This script automatically renames
# all imports after extraction:
#   from ars.analytics.dctr  ->  from ars_analysis.analytics.dctr
#   import ars.config        ->  import ars_analysis.config
#
# HOW IT WORKS
# ------------
# 1. Fetches latest code from the "ars-upstream" git remote
# 2. Extracts source files:  src/ars/  ->  packages/ars_analysis/src/ars_analysis/
#    - Skips: ics/, txn_analysis/, analytics/ics/, analytics/transaction/,
#      ui/, scheduling/, __main__.py  (these are separate monorepo packages)
# 3. Renames imports: "from ars." -> "from ars_analysis." in all .py files
# 4. Extracts test files:  tests/  ->  tests/ars/
#    - Skips: test_ics_runner.py, test_transaction_runner.py
# 5. Renames imports in test files too
# 6. Preserves monorepo-only files (runner.py) by backing up and restoring
#
# FIRST-TIME SETUP (run once)
# ---------------------------
# cd analysis-platform
# git remote add ars-upstream https://github.com/JG-CSI-Velocity/ars-pipeline.git
#
# USAGE
# -----
# ./scripts/sync_ars.sh          Sync latest code (modifies files)
# ./scripts/sync_ars.sh --dry    Preview what would change (no modifications)
#
# AFTER RUNNING
# -------------
# 1. Review changes:     git diff --stat
# 2. Run tests:          uv run pytest tests/ars/ -q
# 3. Fix lint:           uv run ruff check packages/ars_analysis/ tests/ars/ --fix
# 4. Verify imports:     grep -rn 'from ars\.' packages/ars_analysis/src/ tests/ars/
#    (should find ZERO matches -- everything should say "from ars_analysis.")
# 5. Stage and commit:   git add packages/ars_analysis/src/ars_analysis/ tests/ars/
#                         git commit -m "chore(ars): sync from ars-pipeline upstream"
#
# FILES PRESERVED (not overwritten by sync)
# -----------------------------------------
# packages/ars_analysis/src/ars_analysis/runner.py   -- bridge to shared context
# packages/ars_analysis/pyproject.toml               -- monorepo package config
#
# DIRECTORIES EXCLUDED (separate monorepo packages)
# --------------------------------------------------
# src/ars/ics/                  -- ics_toolkit package
# src/ars/txn_analysis/         -- txn_analysis package
# src/ars/analytics/ics/        -- ICS wrapper (removed in monorepo)
# src/ars/analytics/transaction/ -- TXN wrapper (removed in monorepo)
# src/ars/ui/                   -- platform_app package
# src/ars/scheduling/           -- not used
# src/ars/__main__.py           -- monorepo uses different entry point
#
# ============================================================================

set -euo pipefail

REMOTE="ars-upstream"
BRANCH="main"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PKG="packages/ars_analysis/src/ars_analysis"
TEST_DIR="tests/ars"

cd "$REPO_ROOT"

# Check remote exists
if ! git remote | grep -q "^${REMOTE}$"; then
    echo "ERROR: Remote '$REMOTE' not found."
    echo ""
    echo "First-time setup -- run this once:"
    echo "  git remote add $REMOTE https://github.com/JG-CSI-Velocity/ars-pipeline.git"
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

# Directories to EXCLUDE from source sync (separate packages in monorepo)
EXCLUDE_DIRS=(
    "src/ars/ics/"
    "src/ars/txn_analysis/"
    "src/ars/analytics/ics/"
    "src/ars/analytics/transaction/"
    "src/ars/ui/"
    "src/ars/scheduling/"
    "src/ars/__main__.py"
)

# Test files to EXCLUDE
EXCLUDE_TESTS=(
    "tests/test_analytics/test_ics_runner.py"
    "tests/test_analytics/test_transaction_runner.py"
)

# --- Step 1: Sync source code ---
echo "[1/4] Syncing source: src/ars/ -> $SRC_PKG/"
echo "       (excluding ics/, txn_analysis/, ui/, scheduling/)"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- src/ars/ \
        | tar -t \
        | sed 's|^src/ars/||' \
        | grep -v '^$' \
        | grep -v '^ics/' \
        | grep -v '^txn_analysis/' \
        | grep -v '^analytics/ics/' \
        | grep -v '^analytics/transaction/' \
        | grep -v '^ui/' \
        | grep -v '^scheduling/' \
        | grep -v '^__main__.py$' \
        | sed 's/^/    /'
else
    # Back up monorepo-only files
    RUNNER_BACKUP=""
    if [[ -f "$SRC_PKG/runner.py" ]]; then
        RUNNER_BACKUP=$(mktemp)
        cp "$SRC_PKG/runner.py" "$RUNNER_BACKUP"
    fi

    # Extract source files into a temp dir first (so we can filter)
    TMPDIR_SRC=$(mktemp -d)
    git archive "$REMOTE/$BRANCH" -- src/ars/ | tar -x --strip-components=2 -C "$TMPDIR_SRC/"

    # Remove excluded directories from temp extraction
    rm -rf "$TMPDIR_SRC/ics"
    rm -rf "$TMPDIR_SRC/txn_analysis"
    rm -rf "$TMPDIR_SRC/analytics/ics"
    rm -rf "$TMPDIR_SRC/analytics/transaction"
    rm -rf "$TMPDIR_SRC/ui"
    rm -rf "$TMPDIR_SRC/scheduling"
    rm -f  "$TMPDIR_SRC/__main__.py"

    # Copy filtered files into monorepo
    cp -R "$TMPDIR_SRC/"* "$SRC_PKG/"
    rm -rf "$TMPDIR_SRC"

    # Restore monorepo-only files
    if [[ -n "$RUNNER_BACKUP" ]]; then
        cp "$RUNNER_BACKUP" "$SRC_PKG/runner.py"
        rm "$RUNNER_BACKUP"
    fi

    echo "  Done."
fi
echo

# --- Step 2: Rename imports in source files ---
echo "[2/4] Renaming imports: 'from ars.' -> 'from ars_analysis.'"

if $DRY_RUN; then
    echo "  Would rename imports in all .py files under $SRC_PKG/"
    COUNT=$(git archive "$REMOTE/$BRANCH" -- src/ars/ | tar -t | grep '\.py$' | grep -v '^src/ars/ics/' | grep -v '^src/ars/txn_analysis/' | grep -v '^src/ars/ui/' | grep -v '^src/ars/scheduling/' | grep -v '^src/ars/analytics/ics/' | grep -v '^src/ars/analytics/transaction/' | wc -l | tr -d ' ')
    echo "  ~$COUNT Python files to process"
else
    # Rename all "from ars." -> "from ars_analysis." and "import ars." -> "import ars_analysis."
    find "$SRC_PKG" -name '*.py' -exec sed -i '' \
        -e 's/from ars\./from ars_analysis./g' \
        -e 's/from ars import/from ars_analysis import/g' \
        -e 's/import ars\./import ars_analysis./g' \
        -e 's/import ars$/import ars_analysis/g' \
        -e 's/"ars\./"ars_analysis./g' \
        {} +

    # Verify no stale "from ars." imports remain (should be zero)
    STALE=$(grep -rn 'from ars\.' "$SRC_PKG" --include='*.py' 2>/dev/null | grep -v 'ars_analysis' || true)
    if [[ -n "$STALE" ]]; then
        echo "  WARNING: stale 'from ars.' imports found:"
        echo "$STALE" | head -10
    else
        echo "  Done. All imports renamed."
    fi
fi
echo

# --- Step 3: Sync tests ---
echo "[3/4] Syncing tests: tests/ -> $TEST_DIR/"
echo "       (excluding test_ics_runner.py, test_transaction_runner.py)"

if $DRY_RUN; then
    echo "  Files that would be updated:"
    git archive "$REMOTE/$BRANCH" -- tests/ \
        | tar -t \
        | sed 's|^tests/||' \
        | grep -v '^$' \
        | grep -v 'test_ics_runner.py' \
        | grep -v 'test_transaction_runner.py' \
        | sed 's/^/    /'
else
    # Extract tests into temp dir first (so we can filter)
    TMPDIR_TEST=$(mktemp -d)
    git archive "$REMOTE/$BRANCH" -- tests/ | tar -x --strip-components=1 -C "$TMPDIR_TEST/"

    # Remove excluded test files
    rm -f "$TMPDIR_TEST/test_analytics/test_ics_runner.py"
    rm -f "$TMPDIR_TEST/test_analytics/test_transaction_runner.py"

    # Copy filtered tests into monorepo
    cp -R "$TMPDIR_TEST/"* "$TEST_DIR/"
    rm -rf "$TMPDIR_TEST"

    # Rename imports in test files
    find "$TEST_DIR" -name '*.py' -exec sed -i '' \
        -e 's/from ars\./from ars_analysis./g' \
        -e 's/from ars import/from ars_analysis import/g' \
        -e 's/import ars\./import ars_analysis./g' \
        -e 's/import ars$/import ars_analysis/g' \
        -e 's/"ars\./"ars_analysis./g' \
        {} +

    # Verify
    STALE=$(grep -rn 'from ars\.' "$TEST_DIR" --include='*.py' 2>/dev/null | grep -v 'ars_analysis' || true)
    if [[ -n "$STALE" ]]; then
        echo "  WARNING: stale imports in tests:"
        echo "$STALE" | head -10
    else
        echo "  Done. Tests synced and imports renamed."
    fi
fi
echo

# --- Step 4: Sync PPTX template ---
echo "[4/4] Syncing template: src/ars/output/template/ -> $SRC_PKG/output/template/"

if $DRY_RUN; then
    echo "  Would sync Template12.25.pptx"
else
    mkdir -p "$SRC_PKG/output/template"
    git archive "$REMOTE/$BRANCH" -- src/ars/output/template/ 2>/dev/null \
        | tar -x --strip-components=4 -C "$SRC_PKG/output/template/" 2>/dev/null \
        && echo "  Done." \
        || echo "  No template directory in upstream (skipped)."
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
    echo "    2. Test:    uv run pytest tests/ars/ -q"
    echo "    3. Lint:    uv run ruff check packages/ars_analysis/ tests/ars/ --fix"
    echo "    4. Verify:  grep -rn 'from ars\\.' packages/ars_analysis/src/ tests/ars/"
    echo "       (should find ZERO matches -- all should say 'from ars_analysis.')"
    echo "    5. Commit:  git add $SRC_PKG/ $TEST_DIR/"
    echo "                git commit -m 'chore(ars): sync from ars-pipeline upstream ${UPSTREAM_SHA:0:10}'"
fi
echo "=========================================="
