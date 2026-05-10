---
phase: 03
slug: api-fastapi-com-endpoints-de-frequ-ncia
date: 2026-05-08
---

# Phase 03 Validation Strategy

This file defines the validation architecture for Phase 03. Downstream executors must pass these criteria.

## 1. Nyquist Validation Requirements

The following requirements must be verified with automated tests or concrete bash commands before the phase can be considered complete:

| Requirement | Test Method | Success Criteria |
|-------------|-------------|------------------|
| R003: API FastAPI | `curl http://localhost:8000/docs` | Returns 200 with Swagger UI HTML |
| R003: Endpoints | `curl -s "http://localhost:8000/api/groups"` | Returns JSON array of groups |
| R004: Dashboard support | `curl -s "http://localhost:8000/api/stats/top-absent?group_id=X"` | Returns JSON array of stats |
| R005: Isolamento de grupo | `curl -I "http://localhost:8000/api/stats/top-absent"` | Returns HTTP 422 Unprocessable Entity |

## 2. Threat Model Verifications

| Threat ID | Threat Description | Verification Strategy |
|-----------|--------------------|-----------------------|
| T-03-01 | Missing group_id parameter | Verify FastAPI path/query params require group_id (omission yields 422) |
| T-03-02 | Cross-group leakage | Verify `sqlalchemy` queries strictly append `.filter(Model.group_id == group_id)` |

## 3. Pre-Completion Checklist

- [ ] All API endpoints implemented and returning JSON
- [ ] `group_id` parameter enforced on all data queries
- [ ] Swagger documentation automatically updating
