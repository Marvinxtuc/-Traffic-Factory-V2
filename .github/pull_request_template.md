## Summary

Describe what this pull request changes.

## Motivation

Why is this change needed?

## Scope

- [ ] Documentation only
- [ ] Domain model
- [ ] Service layer
- [ ] Workflow orchestration
- [ ] API
- [ ] Web shell
- [ ] Scripts
- [ ] Tests
- [ ] CI / release gate
- [ ] Maintainer automation

## Main Workflow Impact

Does this change affect the fixed workflow?

```text
Signal -> Topic -> Content Variant -> Image Asset -> Publish Check -> Retro Record
```

- [ ] No workflow impact
- [ ] Yes, workflow behavior changed

If yes, explain:

## Validation

Commands run:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Optional smoke check:

```bash
python scripts/current_main_smoke_test.py \
  --base-url http://127.0.0.1:8787
```

## Security Checklist

- [ ] No secrets, tokens, or credentials committed
- [ ] No production data committed
- [ ] No runtime database files committed
- [ ] No sensitive logs committed
- [ ] No workflow gate bypass introduced
- [ ] No publish check bypass introduced
- [ ] No unsafe provider adapter behavior introduced

## Documentation

- [ ] README updated if needed
- [ ] docs updated if needed
- [ ] CONTRIBUTING / SECURITY / AGENTS guidance still accurate
- [ ] Not applicable

## Risk Notes

List known risks, limitations, or follow-up tasks.
