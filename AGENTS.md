# AGENTS.md

## Project Context

Traffic Factory V2 is an open-source, local-first AI workflow infrastructure
project for content operations, workflow orchestration, and agent-assisted
publishing.

The project is built around a strict phase-one workflow:

```text
Signal -> Topic -> Content Variant -> Image Asset -> Publish Check -> Retro Record
```

The matching domain model is:

```text
Signal -> Topic -> ContentVariant -> ImageAsset -> PublishCheck -> RetroRecord
```

## Non-negotiable Workflow Rules

Do not introduce changes that violate these rules:

1. A topic cannot be created without a signal.
2. A content variant cannot be created without a topic.
3. An image asset cannot be created without a content variant.
4. A retro record cannot be created without a publish check.
5. The main workflow cannot skip steps.
6. Every main-chain object must be persisted.
7. Publish checks are hard gates, not advisory hints.
8. When a content variant or image asset changes, the old publish check must be
   invalidated or replaced.

Publish check results are fixed to:

```text
PASS / WARN / BLOCK
```

## Repository Boundaries

Use these boundaries when making changes:

- `app/api/`: API entrypoint and route sets.
- `app/web/pages/`: runtime web page shells and browser-facing workflow actions.
- `app/web/action_bridge.py`: bridge from page actions to API calls.
- `domain/`: domain objects, invariants, status rules, and persistence-facing
  contracts.
- `services/`: application services for the main chain, checks, and capability
  orchestration.
- `workflows/`: main-chain workflow orchestration.
- `skills/` and `adapters/providers/`: minimal skill runtime and provider
  adapter skeletons.
- `scripts/`: database initialization, restart, smoke, and release-check tools.
- `tests/`: unit and integration coverage.
- `docs/`: source-of-truth documentation.
- `stitch/`: design input assets only; not runtime web code.

## Change Discipline

When working in this repository:

1. Keep changes small, explicit, and reviewable.
2. Do not modify business logic when the task only asks for documentation or
   OSS governance changes.
3. Do not modify database schema unless the task explicitly requires it.
4. Do not change runtime defaults unless the task explicitly requires it.
5. Do not bypass tests, release checks, publish checks, or workflow gates.
6. Do not add new production dependencies without explaining why.
7. Do not commit runtime databases, logs, tokens, credentials, or private data.
8. Update documentation when behavior or operating procedures change.

Explicitly forbidden risk patterns include workflow gate bypass, publish check bypass,
committed runtime databases, committed logs, committed tokens, committed
credentials, and committed private data.

## Validation Commands

For most changes, run:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

For runtime validation after startup, run:

```bash
python scripts/current_main_smoke_test.py \
  --base-url http://127.0.0.1:8787
```

For release-oriented validation, follow:

```text
docs/release-checklist.md
docs/current-main-operations.md
```

## Documentation Expectations

When editing documentation:

1. Keep external-facing repository documentation in English.
2. Keep internal workflow terms consistent with the README.
3. Preserve the fixed workflow wording.
4. Avoid unsupported claims about adoption, users, downloads, or production
   usage.
5. Prefer practical operational language over marketing language.

## Pull Request Expectations

Every pull request should explain:

1. What changed
2. Why it changed
3. Which files were affected
4. Whether the main workflow changed
5. Which validation commands were run
6. Any known risks or follow-up tasks
