---
phase: 07-pipeline-build-push-imagens-front-backend
plan: "02"
subsystem: ci-cd
tags: [github-actions, docker, harbor, ci]
dependency_graph:
  requires: [07-01]
  provides: [build-push-workflow]
  affects: [harbor-registry]
tech_stack:
  added: [github-actions, docker/login-action@v3, docker/build-push-action@v6]
  patterns: [parallel-ci-jobs, secret-based-auth]
key_files:
  created: [.github/workflows/build-push.yml]
  modified: []
decisions:
  - "HARBOR_PROJECT set as env var for easy change without touching job steps"
  - "Full SHA used for image tag (not short) — deterministic and collision-free"
  - "Two parallel jobs (no needs: dependency) for faster CI"
metrics:
  started: "2026-05-10T00:51:50Z"
  status: checkpoint-pending
---

# Phase 07 Plan 02: GitHub Actions Build+Push Workflow — Summary

**One-liner:** GitHub Actions CI workflow with two parallel jobs pushing backend/frontend Docker images to Harbor registry on every main push.

## What Was Built

### Task 1 ✅ — Create .github/workflows/build-push.yml

- Created `.github/workflows/` directory and `build-push.yml`
- Workflow triggers on `push` to `main` branch only
- Two parallel jobs: `build-backend` and `build-frontend`
- Each job: checkout → login to Harbor → build+push with two tags (`sha` + `latest`)
- `HARBOR_REGISTRY=harbor.hasslab.pro`, `HARBOR_PROJECT=cell` as env vars
- Credentials via `secrets.HARBOR_USERNAME` and `secrets.HARBOR_PASSWORD` — zero hardcoded creds
- **Commit:** `ffacb3f`

## Status: CHECKPOINT PENDING

Awaiting human verification. See checkpoint details below.

### What User Must Do Before Resuming

1. **Harbor UI** (`harbor.hasslab.pro`): confirm project `cell` exists (create if needed)
2. **Harbor CLI secret:** avatar → User Profile → CLI Secret
3. **GitHub repo** → Settings → Secrets → Actions → add:
   - `HARBOR_USERNAME` = Harbor username
   - `HARBOR_PASSWORD` = Harbor CLI Secret
4. Push a commit to main (or trigger workflow manually via Actions tab)
5. Verify GitHub Actions tab → both jobs green
6. Verify Harbor → Projects → cell → Repositories → `cell-backend` and `cell-frontend` with `:latest`

**Resume signal:** Type "approved" once both Harbor repos show images, or describe any errors.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-07-02-01 | Credentials via GitHub encrypted secrets only — `HARBOR_PASSWORD` maps to CLI Secret |
| T-07-02-03 | Harbor user should have push access to `cell` project only (documented in user_setup) |

## Self-Check

- [x] `.github/workflows/build-push.yml` exists — FOUND
- [x] Commit `ffacb3f` exists
- [x] All verification grep checks passed (registry, secrets, dockerfiles, branch trigger)

## Self-Check: PASSED
