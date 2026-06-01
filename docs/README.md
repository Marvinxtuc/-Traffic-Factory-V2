# Documentation Index

This directory contains phase-one definitions, implementation plans, boundary
notes, audit materials, operations guidance, release checklists, and known-limit
documentation.

It should not contain business code or runtime artifacts.

## Core Documents

1. `phase1-minimal-system-definition.md`
   Phase-one minimal system definition, including the main workflow,
   constraints, domain objects, and boundaries.

2. `phase1-implementation-plan.md`
   Phase-one implementation plan and task-card order.

3. `repo-boundaries.md`
   Repository boundaries, runtime boundaries, testing boundaries, and directory
   responsibilities.

4. `context-pack-v2.md`
   Context continuation and compression reference material.

5. `current-main-operations.md`
   Current main runtime operations, health checks, troubleshooting, and minimal
   rollback runbook.

6. `release-checklist.md`
   Pre-release and post-release checklist for the current main baseline.

7. `current-main-known-limits.md`
   Known limitations and boundary notes for the current version.

## Documentation Rules

The main workflow must remain consistent:

```text
Signal -> Topic -> Content Variant -> Image Asset -> Publish Check -> Retro Record
```

The matching domain model is:

```text
Signal -> Topic -> ContentVariant -> ImageAsset -> PublishCheck -> RetroRecord
```

Publish checks are hard gates.

Publish check status values are fixed to:

```text
PASS / WARN / BLOCK
```

`stitch/` is for design input assets only.

Runtime web pages must live under:

```text
app/web/pages/
```

Runtime databases, logs, local artifacts, and temporary outputs must not be
committed.
