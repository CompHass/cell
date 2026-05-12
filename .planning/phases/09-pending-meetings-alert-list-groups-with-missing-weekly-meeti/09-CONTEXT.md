# Phase 9: Pending Meetings Alert - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a new metric card to the dashboard's existing metrics row (far right) that shows how many groups have pending (unregistered) weekly meetings. The card is only visible when there are pending groups. Clicking it expands a detail view listing each group and the specific weeks with no registered meeting.

</domain>

<decisions>
## Implementation Decisions

### Week Definition
- **D-01:** A week runs Monday to Sunday.
- **D-02:** The alert activates starting from Sunday — once we enter a new Sunday, the previous Monday–Sunday window is checked.
- **D-03:** A meeting is considered "registered" for a week if any event exists in the `events` table with a date within that Monday–Sunday range for the group (no attendance requirement — any event record counts).

### Scope of Pending History
- **D-04:** Check ALL weeks since each group's first recorded event. If a group has no event for any week (Monday–Sunday) from its first event up to last Sunday, that week is flagged as pending.
- **D-05:** No configurable window — full history from first event per group.

### Dashboard Placement
- **D-06:** The pending meetings counter appears as an additional metric card at the far right of the existing metric cards row (alongside Participantes, Presença Média, Em Risco, Qualificados 3×).
- **D-07:** The card is only rendered when there are ≥ 1 pending groups. When all groups are up to date, the card is hidden entirely.
- **D-08:** The card follows the same visual style as the other metric cards (small label + large number).
- **D-09:** Clicking the card expands a detail view (inline below the metrics row, or modal) listing each pending group and the specific weeks they're missing.

### the agent's Discretion
- Label text for the card (e.g., "REUNIÕES PENDENTES" or similar).
- Whether the detail view is an inline expandable section or a modal.
- Color of the number (can use red like "Em Risco" to signal urgency).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend
- `frontend/index.html` — Existing metric cards HTML structure and CSS classes to replicate
- `frontend/app.js` — Existing JS patterns for fetching data and rendering metric cards

### Backend
- `backend/main.py` — Existing FastAPI endpoints and query patterns (event/attendance queries)
- `backend/models.py` — `Event` model (has `date`, `group_id`), `Attendance` model — defines what data is available
- `backend/database.py` — DB session setup

### Data Reference
- `artifacts/extract/` — Historical event data (real events since 2022) — useful to validate the week-gap logic

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Metric card HTML pattern in `frontend/index.html` — small label + large number, same CSS classes to reuse
- `_get_valid_event_ids()` in `backend/main.py` — existing event validity logic (not required here since any event counts, but pattern is reusable)
- `fetchJSON()` in `frontend/app.js` — existing async fetch helper to use for new endpoint

### Established Patterns
- All endpoints filter by `group_id`; new endpoint must accept `group_id` as query param (or list of group IDs) consistent with existing API
- FastAPI + SQLAlchemy query pattern: `db.query(Model).filter(...).all()` — follow existing style
- Frontend fetches data on page load and on filter change; pending meetings card should update with same lifecycle

### Integration Points
- New FastAPI endpoint (e.g., `GET /pending-meetings`) returning count + list of pending groups with their missing weeks
- Frontend hooks into the existing metrics row DOM — append new card after the last existing metric card
- Filter bar: if a group filter is active, the pending meetings check should respect that filter (show pending only for selected groups)

</code_context>

<specifics>
## Specific Ideas

- Screenshot of current dashboard provided — metric cards row: Participantes / Presença Média / Em Risco / Qualificados 3× — new card goes at the far right end of this row.
- User confirmed: card appears only when there are pending groups; no "all good" state shown.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-pending-meetings-alert-list-groups-with-missing-weekly-meeti*
*Context gathered: 2026-05-12*
