# Phase 03 Research

## Objective
How to implement Phase 03: API FastAPI com endpoints de frequência.

## Requirements Mapping
- **R003**: Endpoints REST para consulta de frequência.
- **R005**: Todas as queries e views filtram por `group_id` (mandatório).

## Technical Approach
- **Framework**: FastAPI (python)
- **Server**: Uvicorn
- **ORM**: SQLAlchemy (already setup in `backend/models.py` and `backend/database.py`)
- **Data Flow**: The dashboard (Phase 04) will call these endpoints. 

### Endpoints to build
1. `GET /api/groups`: Return available groups for the UI dropdown.
2. `GET /api/stats/top-absent`: Group by person_id, count status='absent' in the last 2 months. Required param: `group_id`.
3. `GET /api/stats/top-present`: Group by person_id, count status='present' all time. Required param: `group_id`.
4. `GET /api/stats/attendance-by-week`: Group by week of month, count 'present' and 'absent' for a specific month. Required param: `group_id`.

## Security & Constraints
- **R005 Constraint**: Every endpoint in `/api/stats/*` MUST accept a `group_id` query parameter and append `.filter(Model.group_id == group_id)` to every SQLAlchemy query. No exception.
- **CORS**: Since Phase 05 uses Docker Compose (and FastAPI will serve static files), we should configure permissive CORS for development.

## Implementation Steps
1. Add `fastapi` and `uvicorn` to `backend/requirements.txt` (or root `requirements.txt`).
2. Create `backend/main.py` defining the FastAPI app.
3. Write the analytic queries using `sqlalchemy.sql.func`.

## Validation Architecture
- Unit tests or `curl` calls testing each endpoint.
- Verify `group_id` isolation: requesting stats without `group_id` should throw a `422 Validation Error` or `400 Bad Request`.
