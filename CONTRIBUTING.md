# Contributing to Dify Plugin Repackaging

Thank you for your interest in contributing to the Dify Plugin Repackaging tool! We welcome contributions from the community.

## Code of Conduct

Please be respectful, inclusive, and considerate in all interactions.

## How Can I Contribute?

### Reporting Bugs
- Check if the bug has already been reported
- Create a new issue with clear description and steps to reproduce
- Include environment details (OS, Python version, Docker version)

### Suggesting Features
- Create a new issue with the "enhancement" label
- Describe the feature and its benefits clearly

### Contributing Code
- Fix bugs, implement features, improve security
- Follow coding standards and write tests

## Development Setup

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18 or 20
- Docker and Docker Compose
- Redis
- Git

### Backend Setup
```bash
cd dify-plugin-repackaging-web/backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd dify-plugin-repackaging-web/frontend
npm install
npm run dev
```

## Coding Standards

### Python
- Follow PEP 8
- Use type hints
- Use async/await for I/O operations
- Run: `black . && isort . && mypy .`

### JavaScript/React
- Follow ESLint and Prettier
- Use functional components with hooks
- Run: `npm run lint && npm run format`

### Bash
- Follow ShellCheck recommendations
- Quote variables, check errors
- Run: `shellcheck plugin_repackaging.sh`

## Security Guidelines (CRITICAL)

### Input Validation
```python
# GOOD: Whitelist validation
ALLOWED_PLATFORMS = ["manylinux_2_17_x86_64", "manylinux2014_x86_64"]
if platform not in ALLOWED_PLATFORMS:
    raise ValueError(f"Invalid platform")
```

### Command Injection Prevention
```python
# GOOD: Use list format
cmd = ["pip", "download", "--platform", validated_platform]
subprocess.run(cmd, check=True)

# BAD: NEVER do this
os.system(f"pip download --platform {platform}")  # Command injection!
```

### Path Traversal Protection
```python
# GOOD: Validate paths
def safe_path_join(base_dir: str, user_path: str) -> Path:
    base = Path(base_dir).resolve()
    full_path = (base / user_path).resolve()
    if not full_path.is_relative_to(base):
        raise ValueError("Path traversal detected")
    return full_path
```

## Testing Requirements

- Backend: 80% coverage minimum
- Frontend: 70% coverage minimum

```bash
# Backend tests
pytest --cov=app --cov-report=html

# Frontend tests
npm test && npm run test:e2e
```

## Pull Request Process

1. Fork and create a branch: `git checkout -b feature/your-feature`
2. Make changes with tests and documentation
3. Run tests and linters
4. Commit using conventional commits
5. Push and create PR

### Commit Messages
```
feat: add plugin verification
fix: resolve upload error
docs: update API guide
test: add integration tests
```

## Questions?

Create an issue with the "question" label.

Thank you for contributing!
