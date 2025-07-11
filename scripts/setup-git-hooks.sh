#!/bin/bash
# Setup git hooks for the project

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository!"
    exit 1
fi

GIT_DIR=$(git rev-parse --git-dir)
HOOKS_DIR="$GIT_DIR/hooks"

log_info "Setting up git hooks..."

# Create pre-push hook
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to run quick tests

echo "Running pre-push checks..."

# Run quick unit tests
echo "Running quick unit tests..."
make quick-test

if [ $? -ne 0 ]; then
    echo "Tests failed! Push aborted."
    echo "Run 'make test' to see full test results."
    exit 1
fi

echo "Pre-push checks passed!"
EOF

chmod +x "$HOOKS_DIR/pre-push"
log_info "Created pre-push hook"

# Create commit-msg hook for conventional commits
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# Commit message hook to enforce conventional commits

commit_regex='^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .{1,50}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "Invalid commit message format!"
    echo ""
    echo "Commit message must follow conventional commits format:"
    echo "  <type>(<scope>): <subject>"
    echo ""
    echo "Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert"
    echo ""
    echo "Example: feat(backend): add webhook support"
    echo ""
    exit 1
fi
EOF

chmod +x "$HOOKS_DIR/commit-msg"
log_info "Created commit-msg hook"

# Create prepare-commit-msg hook
cat > "$HOOKS_DIR/prepare-commit-msg" << 'EOF'
#!/bin/bash
# Prepare commit message with branch info

BRANCH_NAME=$(git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')

# Skip if it's a merge, squash, or amend
case "$2" in
  merge|squash|fixup)
    exit 0
    ;;
esac

# Extract issue number from branch name (e.g., feature/123-add-feature -> #123)
ISSUE_NUMBER=$(echo "$BRANCH_NAME" | grep -oE '[0-9]+' | head -n1)

if [ -n "$ISSUE_NUMBER" ]; then
    # Check if issue number is already in the message
    if ! grep -q "#$ISSUE_NUMBER" "$1"; then
        # Add issue number to the end of the first line
        sed -i.bak -e "1s/$/ (#$ISSUE_NUMBER)/" "$1"
    fi
fi
EOF

chmod +x "$HOOKS_DIR/prepare-commit-msg"
log_info "Created prepare-commit-msg hook"

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    log_warning "pre-commit not found. Installing..."
    pip install pre-commit
fi

# Install pre-commit hooks
log_info "Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Run pre-commit on all files to check current state
log_info "Running pre-commit on all files to check current state..."
pre-commit run --all-files || log_warning "Some pre-commit checks failed. Run 'make format' to fix."

log_info "Git hooks setup complete!"
log_info ""
log_info "Hooks installed:"
log_info "  - pre-commit: Code quality checks (via pre-commit framework)"
log_info "  - commit-msg: Conventional commit format enforcement"
log_info "  - prepare-commit-msg: Auto-add issue numbers from branch names"
log_info "  - pre-push: Quick unit tests before push"
log_info ""
log_info "To skip hooks temporarily, use --no-verify flag"