# Contributing to AIOps Skills

Thank you for your interest in contributing to the AIOps Skills marketplace! This guide will help you get started with development, testing, and submitting contributions.

## Prerequisites

- **Python 3.10+** (3.10, 3.11, or 3.12)
- **Git** for version control
- **GitHub account** for submitting pull requests
- Optional: [GitHub CLI](https://cli.github.com/) for easier PR management

## Project Structure

The repository is organized as follows:

```
aiops-skills/
├── docs/
│   └── agent_skills_spec.md    # Skill format specification
├── template-skill/         # Minimal skill template
├── skills/
│  ├── <skill-name>/           # Individual skills (e.g., logs-fetcher)
│   ├── SKILL.md            # Required: skill entrypoint with frontmatter
│   ├── scripts/            # Optional: Python scripts
│   └── tests/              # Recommended: skill-specific tests
├── tests/                  # Test directory
└── pyproject.toml          # Project configuration and dependencies
```

See [CLAUDE.md](CLAUDE.md) for detailed project overview and [agent_skills_spec.md](agent_skills_spec.md) for complete skill specification.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/redhat-et/aiops-skills.git
cd aiops-skills
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
3. Install Development Dependencies
```

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies including:

- `pytest` and `pytest-cov` for testing
- `ruff` for linting and formatting
- `mypy` for type checking
- `bandit` for security scanning
- 'gitleaks' for secrets scanning

This sets up automatic code quality checks that run before each commit.

### 4. Verify Your Setup

```bash
# Run tests
pytest tests/ -v

# Check linting
ruff check .
```

## Running Tests

The project uses `pytest` for testing. Tests are organized by skill in the `tests/` directory.

### Run All Tests

```bash
pytest tests/ -v
```

### Run Tests for a Specific Skill

```bash
# Example: root-cause-analysis tests
pytest tests/root-cause-analysis/ -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov
```

### Test Configuration

Test settings are defined in `pyproject.toml` under `[tool.pytest.ini_options]`. The test suite:

- Auto-discovers tests in the `tests/` directory
- Uses verbose output by default
- Tracks coverage for the project

## Code Style

The project enforces consistent code style using **Ruff** for linting and formatting, and **mypy** for type checking.

### Linting with Ruff

**Check for linting issues:**

```bash
ruff check .
```

**Auto-fix linting issues:**

```bash
ruff check . --fix
```

**Format code:**

```bash
ruff format .
```

**Configuration:**

- Line length: 100 characters
- Target: Python 3.10+
- Settings in `pyproject.toml` under `[tool.ruff]`

### Type Checking with Mypy

```bash
# Type check a specific skill
mypy root-cause-analysis/scripts/

# Type check all Python files
mypy .
```

Type checking configuration is in `pyproject.toml` under `[tool.mypy]`.

### Security Scanning with Bandit

Bandit checks for common security issues such as hardcoded passwords, use of unsafe functions, and shell injection risks. It runs automatically on commit via pre-commit hooks.

**Run manually:**

```bash
# Scan all Python files
bandit -c pyproject.toml -r .

# Scan a specific skill's scripts
bandit -c pyproject.toml -r root-cause-analysis/scripts/
```

**Configuration:**

- Minimum severity reported: `medium`
- Minimum confidence reported: `medium`
- Excluded directories: `tests/`, `.venv/`
- Settings in `pyproject.toml` under `[tool.bandit]`

## Creating a New Skill

### 1. Start with the Template

Copy the `template-skill/` directory as a starting point:

```bash
cp -r template-skill/ my-skill/
cd my-skill/
```

### 2. Required Directory Structure

```
my-skill/
├── SKILL.md       # Required: skill definition
├── scripts/       # Optional: Python implementation
│   └── my_script.py
└── tests/         # Recommended: skill tests
    └── test_my_script.py
```

### 3. Creating a New Skill

1. Create a directory under `skills/` with your skill name (lowercase, hyphen-separated)
2. Add a `SKILL.md` file:

```markdown
---
name: my-skill
description: Brief description of what this skill does
allowed-tools:
  - Bash
  - Read
---

# My Skill

Instructions for Claude...
```

See [template-skill](./template-skill/) for a minimal example and [agent_skills_spec.md](./agent_skills_spec.md) for the full specification.

## License

Individual skills may specify their own licenses in frontmatter.

## Troubleshooting

Common issues and solutions...

```

### 4. Add Tests

Create tests in `tests/my-skill/`:

```python
# tests/my-skill/test_my_script.py
import pytest
from my_skill.scripts.my_script import my_function

def test_my_function():
    result = my_function("input")
    assert result == "expected_output"
```

### 5. Update Documentation

Add your skill to the README.md skill list.

### 6. Reference Documentation

See [agent_skills_spec.md](agent_skills_spec.md) for the complete skill specification.

## Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/my-contribution
```

Branch naming conventions:

- `feature/description` - New features or skills
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates

### 2. Make Your Changes

Follow the code style guidelines and ensure your changes:

- Are well-documented
- Include tests for new functionality
- Update relevant documentation
- Do not commit `.env` files, credentials, tokens, or secrets of any kind
- Always use clearly fake placeholder values in examples — never real hostnames, job IDs, usernames, or tokens. Use values like `example.com`, `job-12345`, `user@example.com`, `my-namespace`, or `xxx-xxx-xxx-xxx` for GUIDs.

### 3. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Run tests
pytest tests/ -v

# Check linting
ruff check . && ruff format .

# Type checking
mypy <skill>/scripts/

# Security scanning - checks Python code for hardcoded passwords, unsafe functions 
bandit -c pyproject.toml -r <skill>/scripts/

# Secrets scan - checks all file types for tokens, keys, and credentials
gitleaks detect --source .
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add new skill for X functionality"
```

The pre-commit hooks will automatically run. Fix any issues they report.

### 5. Push and Create Pull Request

```bash
git push origin feature/123-my-contribution
```

Then create a pull request on GitHub with:

- **Clear title**: Summarize the change
- **Description**: Explain what, why, and how
- **Testing**: Describe how you tested the changes
- **Related issues**: Link to any related issues

### 6. CI/CD Checks

The CI pipeline will automatically run three jobs:

1. **Lint** (Python 3.12): Runs `ruff check` and `ruff format --check`
2. **Test** (Python 3.10, 3.11, 3.12): Runs `pytest` with coverage
3. **Typecheck** (Python 3.12): Runs `mypy` (continues on error)

**Your PR must pass linting and testing to be merged.**

### 7. Address Feedback

- Respond to reviewer comments
- Make requested changes
- Push updates to your branch (the PR will auto-update)
- Re-request review when ready

### 8. Merge

Once approved and all checks pass, a maintainer will merge your PR.

## Getting Help

- **Bug reports:** Open a [GitHub Issue](https://github.com/redhat-et/aiops-skills/issues)

