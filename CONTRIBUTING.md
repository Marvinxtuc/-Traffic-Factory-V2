# Contributing to Traffic Factory V2

Thank you for your interest in contributing to Traffic Factory V2.

Traffic Factory V2 is an open-source, local-first AI workflow infrastructure
project for content operations, workflow orchestration, and agent-assisted
publishing.

The project is intentionally small, explicit, auditable, and testable.
Contributions should improve maintainability without weakening the fixed
workflow or release gates.

## Development Principles

Contributions should follow these principles:

1. Keep changes small, reviewable, and testable.
2. Preserve the fixed main workflow:

```text
Signal -> Topic -> Content Variant -> Image Asset -> Publish Check -> Retro Record
```

3. Do not bypass publish checks or workflow gates.
4. Do not introduce hidden coupling across domain boundaries.
5. Keep runtime data, secrets, tokens, credentials, and production artifacts out
   of the repository.
6. Prefer explicit state transitions over implicit side effects.
7. Update documentation when behavior, commands, boundaries, or release
   procedures change.

## Local Setup

Use Python 3.11 or newer.

Check your Python version:

```bash
python --version
```

Create and activate a virtual environment if needed:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn requests beautifulsoup4 feedparser httpx
```

Initialize the local SQLite database:

```bash
python scripts/init_db.py
```

Start the local runtime:

```bash
python -m app.main \
  --host 127.0.0.1 \
  --port 8787 \
  --db-path data/runtime/traffic_factory.sqlite3
```

## Running Tests

Run the full test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

After starting the runtime, run the smoke check:

```bash
python scripts/current_main_smoke_test.py \
  --base-url http://127.0.0.1:8787
```

For release-oriented validation, see:

```text
docs/release-checklist.md
docs/current-main-operations.md
```

## Reporting Issues

When opening an issue, please include:

- Expected behavior
- Actual behavior
- Steps to reproduce
- Environment details
- Relevant logs or screenshots
- Whether the issue affects workflow gates, persistence, API behavior, web
  shell behavior, or release checks

Please remove secrets, tokens, credentials, private data, and runtime database
content before submitting an issue.

## Pull Request Guidelines

Before opening a pull request:

1. Keep the PR focused on one problem.
2. Explain the motivation and scope.
3. Update documentation when behavior changes.
4. Add or update tests for workflow, service, API, persistence, or release-gate
   changes.
5. Run the full test suite locally.
6. Confirm no secrets, tokens, credentials, runtime database files, or private
   data are committed.
7. Confirm the fixed workflow has not been bypassed.

## Main Workflow Invariants

The following invariants must remain true:

1. A topic cannot be created without a signal.
2. A content variant cannot be created without a topic.
3. An image asset cannot be created without a content variant.
4. A retro record cannot be created without a publish check.
5. The main workflow cannot skip steps.
6. Every main-chain object must be persisted.
7. Publish checks are hard gates, not advisory hints.
8. When content or image assets change, prior publish checks must be invalidated
   or replaced.

## Security

Please do not report security vulnerabilities through public issues.

See `SECURITY.md` for responsible disclosure guidance.
