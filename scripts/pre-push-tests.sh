#!/bin/bash
# =============================================================================
# ClarityGR Pre-Push Sanity Tests
# =============================================================================
# Run this script before pushing to ensure critical functionality works.
#
# Usage:
#   ./scripts/pre-push-tests.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - Tests failed, do not push
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🧪 ClarityGR Pre-Push Sanity Checks"
echo "===================================="
echo ""

cd "$PROJECT_ROOT"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected. Activating if available..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
fi

echo "📍 Project root: $PROJECT_ROOT"
echo "🐍 Python: $(which python)"
echo ""

# Run sanity tests
echo "🔍 Running sanity tests..."
echo "-----------------------------------"

if python -m pytest tests/sanity/ -v --tb=short; then
    echo ""
    echo "✅ All sanity checks PASSED!"
    echo "   You can safely push your changes."
    exit 0
else
    echo ""
    echo "❌ Sanity checks FAILED!"
    echo "   Please fix the failing tests before pushing."
    exit 1
fi

