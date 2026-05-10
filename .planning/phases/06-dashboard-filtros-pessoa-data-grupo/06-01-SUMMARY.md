# 06-01 Summary — FastAPI Filter Params

**Status:** Complete  
**Files modified:** `backend/main.py`

## What was done
Added `date_from`, `date_to`, `person_name` query params to all 3 endpoints:
- `/api/top-absent` — date range replaces hardcoded 60-day cutoff; person ilike filter added
- `/api/attendance-by-week` — date range + person filter (via Person join)
- `/api/top-present` — date range + person ilike filter

## Verification
- `python -c "from backend.main import app; print('import OK')"` → OK
- `grep -c "date_from" backend/main.py` → 9
- `grep -c "person_name" backend/main.py` → 9
- `curl /api/top-present?date_from=2024-01-01&date_to=2024-12-31` → filtered results ✓
- `curl /api/top-present?person_name=Eduardo` → single person result ✓
