---
phase: 07-pipeline-build-push-imagens-front-backend
plan: "01"
subsystem: docker
tags: [docker, ci, frontend, backend, nginx]
dependency_graph:
  requires: []
  provides: [Dockerfile.backend, Dockerfile.frontend]
  affects: [ci-pipeline]
tech_stack:
  added: [nginx:1.25-alpine]
  patterns: [multi-dockerfile, separate-ci-images]
key_files:
  created: [Dockerfile.backend, Dockerfile.frontend]
  modified: []
decisions:
  - "Dockerfile.backend = identical copy of Dockerfile — no logic change, CI-tagged artifact"
  - "Dockerfile.frontend = nginx:1.25-alpine with try_files SPA routing — pure static image"
  - "Original Dockerfile untouched — docker-compose.yml workflow unchanged"
metrics:
  duration: "~5min"
  completed: "2026-05-09"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 07 Plan 01: Dockerfiles backend e frontend para CI Summary

## One-Liner

Split Dockerfile into Dockerfile.backend (Python/Playwright/FastAPI port 8000) and Dockerfile.frontend (nginx:1.25-alpine SPA port 80) for independent CI image builds to harbor.hasslab.pro.

## What Was Built

Two purpose-specific Dockerfiles for the CI/CD image registry pipeline:

- **Dockerfile.backend** — identical to existing `Dockerfile`; CI-tagged backend image source with Python/Playwright, FastAPI, entrypoint.sh
- **Dockerfile.frontend** — nginx:1.25-alpine serving `frontend/` static files; SPA routing via `try_files`

Original `Dockerfile` and `docker-compose.yml` are untouched.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Dockerfile.backend | cf58537 | Dockerfile.backend |
| 2 | Create Dockerfile.frontend | 7be411f | Dockerfile.frontend |

## Verification

All three builds passed:
```
backend OK
frontend OK
original OK
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] Dockerfile.backend exists and builds
- [x] Dockerfile.frontend exists and builds
- [x] Original Dockerfile untouched
- [x] Commits cf58537, 7be411f confirmed in git log
