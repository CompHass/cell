# Phase 02: Schema Postgres + Migração Histórica

## Requirements
- R002: Storage Postgres multi-grupo (`groups`, `events`, `attendance` com `group_id` obrigatório). Upsert idempotente.
- R006: Migração dos dados históricos lendo de `artifacts/extract/attendance_rows.ndjson` e `event_summary.json`.

## Entity Schema
- **groups**: `id` (VARCHAR PK), `name` (VARCHAR).
- **persons**: `id` (VARCHAR PK), `name` (VARCHAR), `group_id` (VARCHAR).
- **events**: `id` (VARCHAR PK), `date` (TIMESTAMP), `name` (VARCHAR), `group_id` (VARCHAR).
- **attendance**: `event_id` (VARCHAR FK), `person_id` (VARCHAR FK), `status` (VARCHAR), `group_id` (VARCHAR). PK is `(event_id, person_id)`.

## Tools
- `psycopg2` or `asyncpg` + `sqlalchemy`. We'll use synchronous `psycopg2-binary` and `SQLAlchemy` for the migration script, since the API later will use FastAPI + SQLAlchemy.
- Migração via `scripts/migrate_history.py` - Lê JSON/ndjson e usa `INSERT ... ON CONFLICT DO UPDATE` (upsert) do PostgreSQL para ser idempotente.

## Validation Architecture
- Test with local Postgres via `docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine`
- Validate rows inserted.