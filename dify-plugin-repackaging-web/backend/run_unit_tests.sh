#!/bin/bash
# Run unit tests for the dify-plugin-repackaging backend

set -e

echo "🧪 Running unit tests for dify-plugin-repackaging backend..."
echo "=================================================="

# Set test environment
export TESTING=true
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Install test dependencies if needed
if [ "$1" == "--install" ]; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run different test suites based on argument
case "${1:-all}" in
    "unit")
        echo "🔬 Running unit tests only..."
        pytest tests/unit -v --tb=short
        ;;
    "integration")
        echo "🔗 Running integration tests only..."
        pytest tests/integration -v --tb=short
        ;;
    "api")
        echo "🌐 Running API tests only..."
        pytest tests/unit/api -v --tb=short
        ;;
    "services")
        echo "⚙️ Running service tests only..."
        pytest tests/unit/services -v --tb=short
        ;;
    "core")
        echo "🏗️ Running core tests only..."
        pytest tests/unit/core -v --tb=short
        ;;
    "coverage")
        echo "📊 Running tests with coverage report..."
        pytest tests/unit --cov=app --cov-report=html --cov-report=term-missing
        echo "📁 Coverage report generated in htmlcov/"
        ;;
    "watch")
        echo "👁️ Running tests in watch mode..."
        pytest-watch tests/unit -- -v --tb=short
        ;;
    "parallel")
        echo "🚀 Running tests in parallel..."
        pytest tests/unit -n auto -v --tb=short
        ;;
    "all"|"--install")
        echo "🏃 Running all unit tests..."
        pytest tests/unit -v
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  api         - Run API endpoint tests only"
        echo "  services    - Run service layer tests only"
        echo "  core        - Run core component tests only"
        echo "  coverage    - Run tests with coverage report"
        echo "  watch       - Run tests in watch mode (requires pytest-watch)"
        echo "  parallel    - Run tests in parallel"
        echo "  all         - Run all unit tests (default)"
        echo "  --install   - Install test dependencies first"
        echo "  help        - Show this help message"
        exit 0
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tests passed successfully!"
else
    echo ""
    echo "❌ Tests failed!"
    exit 1
fi