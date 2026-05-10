---
phase: 08-etl-cronjob-kubernetes
plan: 02
subsystem: kubernetes/etl
tags: [kubernetes, cronjob, etl, batch]
dependency_graph:
  requires: [08-01]
  provides: [k8s/etl-cronjob.yaml]
  affects: [cell namespace, daily ETL schedule]
tech_stack:
  added: []
  patterns: [Kubernetes CronJob, envFrom secretRef, imagePullSecrets]
key_files:
  created: [k8s/etl-cronjob.yaml]
  modified: []
decisions:
  - "concurrencyPolicy: Forbid — prevents overlapping ETL runs"
  - "set -e in shell command — extract failure blocks migrate (no partial loads)"
  - "Ephemeral pod filesystem sufficient — artifacts/ transient per run"
  - "backoffLimit: 2 — retry twice before marking job failed"
metrics:
  duration: ~5m
  completed: 2026-05-09
  tasks_completed: 1
  tasks_total: 1
---

# Phase 08 Plan 02: Kubernetes CronJob ETL — Summary

**One-liner:** CronJob `cell-etl` scheduled `0 0 * * *` running extract.py→migrate_history.py via `set -e`, envFrom `cell-secret`, `concurrencyPolicy: Forbid`.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create k8s/etl-cronjob.yaml | daf6d37 | k8s/etl-cronjob.yaml |

## What Was Built

`k8s/etl-cronjob.yaml` — Kubernetes CronJob manifest ready for `kubectl apply`:

- **Schedule:** `0 0 * * *` (midnight UTC daily)
- **Namespace:** `cell`
- **Image:** `harbor.hasslab.pro/cell/cell-backend:latest`
- **Command:** `/bin/sh -c "set -e; python scripts/extract.py; python scripts/migrate_history.py"`
- **envFrom:** `secretRef: cell-secret` (DATABASE_URL + CELULA_*)
- **imagePullSecrets:** `harbor-pull-secret`
- **concurrencyPolicy:** `Forbid`
- **backoffLimit:** 2
- **History:** 3 successful / 3 failed jobs retained
- **Resources:** requests 256Mi/100m, limits 1Gi/500m

## Verification

```
kubectl apply --dry-run=client -f k8s/etl-cronjob.yaml
# → cronjob.batch/cell-etl created (dry run)
```

All field checks passed: schedule, secret ref, pull secret, image, restartPolicy, concurrencyPolicy.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| T-ID | Mitigation |
|------|-----------|
| T-08-02-01 | envFrom secretRef — creds never in manifest plaintext |
| T-08-02-02 | concurrencyPolicy: Forbid + historyLimits — no pod accumulation |
| T-08-02-03 | set -e — extract failure halts pipeline before migrate |

## Self-Check: PASSED

- [x] `k8s/etl-cronjob.yaml` exists
- [x] Commit `daf6d37` exists in git log
- [x] kubectl dry-run: `cronjob.batch/cell-etl created (dry run)`
