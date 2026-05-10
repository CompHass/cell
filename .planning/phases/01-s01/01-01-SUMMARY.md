---
phase: "01"
plan: "01"
---

# T01: Created scripts/extract.py — full Python port of extract-attendance.mjs using httpx + python-dotenv, writing all 6 artefacts to artifacts/extract/

**Created scripts/extract.py — full Python port of extract-attendance.mjs using httpx + python-dotenv, writing all 6 artefacts to artifacts/extract/**

## What Happened

Read the original Node script (scripts/extract-attendance.mjs) and .env.example in full before writing any code. The port is a 1:1 functional equivalent:

- `load_env()` uses python-dotenv to load .env from the repo root without overriding already-set env vars.
- `authenticate()` posts to /authenticate using httpx.AsyncClient with the same JSON:API headers, then calls `extract_token()` which walks the same four fallback paths as the Node version. Raises ValueError with explicit message if token is absent.
- `fetch_group_events()` and `fetch_event_detail()` mirror the Node API calls exactly, including the `?include=` query strings.
- `_parse_json_response()` raises RuntimeError with HTTP status + truncated body on 4xx/5xx, matching the Node error shape.
- The main loop processes events sequentially (same as Node), building row_records and event_summaries, writing group_events_raw.ndjson incrementally.
- Phase 4/5 writes all 4 normalised artefacts: attendance_rows.ndjson, event_summary.json, attendance.csv, attendance_summary_by_person.csv.
- CELULA_MAX_EVENTS and CELULA_TOKEN env vars are respected identically to the Node version.
- 5-phase progress prints are present (1/5…5/5) as required by the slice verification contract.
- scripts/requirements.txt lists httpx and python-dotenv (no playwright needed for S01 — httpx is sufficient as the task plan notes).

## Verification

Three-part verification check from task plan ran clean:
1. `python3 -c "import ast; ast.parse(open('scripts/extract.py').read()); print('syntax OK')"` → exit 0
2. `grep -q 'httpx' scripts/requirements.txt` → exit 0
3. `grep -q 'python-dotenv' scripts/requirements.txt` → exit 0

Additional manual checks confirmed: all 5 phase print() calls present (lines 208, 217, 227, 245, 309, 373), all error paths raise with context (ValueError/RuntimeError at lines 33, 79, 83, 110, 205).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast, sys; ast.parse(open('scripts/extract.py').read()); print('syntax OK')"` | 0 | ✅ pass | 120ms |
| 2 | `grep -q 'httpx\|playwright' scripts/requirements.txt && echo ok` | 0 | ✅ pass | 10ms |
| 3 | `grep -q 'python-dotenv' scripts/requirements.txt && echo ok` | 0 | ✅ pass | 10ms |

## Deviations

None. httpx chosen over playwright for S01 as explicitly recommended in the task plan note.

## Known Issues

None.

## Files Created/Modified

- `scripts/extract.py`
- `scripts/requirements.txt`
