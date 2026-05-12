---
phase: 09-pending-meetings-alert-list-groups-with-missing-weekly-meeti
plan: "01"
subsystem: backend
tags: [api, week-gap-detection, meetings]
key-files:
  modified:
    - backend/main.py
decisions:
  - "Used venv/bin/python3.14 -m uvicorn instead of venv/bin/uvicorn (bad interpreter shebang in venv)"
metrics:
  completed: "2026-05-12"
  tasks: 2
  commits: 1
---

# Phase 09 Plan 01: Pending Meetings Endpoint Summary

Add `GET /api/pending-meetings` with week gap detection for Mon–Sun history per group.

## What Was Done

**Task 1 — Week helper functions**
- Changed `from datetime import datetime, timedelta` → `from datetime import datetime, timedelta, date as _date` (line 6)
- Inserted 3 helpers before `_get_valid_event_ids` (line 33):
  - `_get_monday(d)` — returns Monday of week containing d
  - `_last_sunday(today)` — returns most recent Sunday (UTC)
  - `_all_weeks_since(first_event_dt, ref_sunday)` — yields (monday, sunday) pairs

**Task 2 — Endpoint**
- Inserted `@app.get("/api/pending-meetings")` after `/api/at-risk` block (before `/api/person-week-heatmap`)
- Full implementation: group scoping → first-event aggregation → covered-set build → missing week enumeration → ISO week label formatting

## Smoke Test Output

```
endpoint shape OK, count= 2
filter OK
```

- HTTP 200 on both calls
- `count=2` groups with missing weeks found in real data
- `?group_id=nonexistent_xyz` → `{count: 0, groups: []}` ✓
- Week format validated (`YYYY-Www`) ✓

## Deviations from Plan

**1. [Rule 3 - Blocker] venv uvicorn shebang pointed to deleted python path**
- Found during: Task 2 verify
- Issue: `venv/bin/uvicorn` shebang referenced `/Users/hass/repos/github/comphass/cell_frequency/venv/bin/python3.14` (old path) — bad interpreter
- Fix: Used `venv/bin/python3.14 -m uvicorn` instead
- No code change needed

**2. Commit message shortened**
- Project hook enforces ≤70 char subject; adjusted from plan's suggested message

## Self-Check: PASSED

- `backend/main.py` modified ✓
- Commit `511fbfa` exists ✓
- Import OK ✓
- Helpers assertions pass ✓
- Endpoint shape + filter assertions pass ✓
