# Phase 9: Pending Meetings Alert — Research

**Researched:** 2026-05-12
**Domain:** FastAPI endpoint + SQLAlchemy date logic + frontend KPI card insertion
**Confidence:** HIGH — all findings from direct codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Week = Monday–Sunday
- D-02: Alert activates on Sunday; previous Mon–Sun window is checked
- D-03: "Registered" = any event row for group with date in Mon–Sun range (no attendance requirement)
- D-04: Check ALL weeks since each group's first recorded event
- D-05: No configurable window — full history from first event per group
- D-06: Card goes far right of `.kpi-grid` (after Qualificados 3×)
- D-07: Card hidden when 0 pending groups
- D-08: Same visual style as other kpi-cards
- D-09: Click expands detail view listing each pending group + missing weeks

### Agent's Discretion
- Label text (e.g. "REUNIÕES PENDENTES")
- Detail view: inline expandable or modal
- Number color (red like "Em Risco" recommended for urgency)

### Deferred Ideas
None
</user_constraints>

---

## Summary

Phase 9 adds a `GET /api/pending-meetings` endpoint that computes, per group, every Monday–Sunday week from the group's first event to last Sunday that has no event row. The frontend adds one KPI card (hidden when count=0) to the existing `.kpi-grid` that shows the count of affected groups; clicking it expands an inline detail panel.

All patterns already exist in the codebase and can be replicated exactly. No new libraries needed.

**Primary recommendation:** Add endpoint to `backend/main.py` following the `@app.get("/api/at-risk")` style; add card HTML inside `.kpi-grid` after the 4th card; add `loadPendingMeetings()` call inside `loadOverview()` alongside the existing `Promise.all`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Week-gap computation | API / Backend | — | Requires full event history from DB; too heavy for client |
| Group filtering | API / Backend | Frontend filter bar | `group_id` query param, consistent with all endpoints |
| KPI card render | Browser / Client | — | Injected into DOM via innerHTML, same as stat-total/stat-critical |
| Detail list (missing weeks) | Browser / Client | — | Rendered from endpoint response; no separate endpoint needed |

---

## 1. Exact HTML Structure — KPI Cards

**File:** `frontend/index.html` lines 576–627

The `.kpi-grid` is a CSS Grid with `grid-template-columns: repeat(4, 1fr)` (line 221). Each card:

```html
<!-- EXACT pattern — lines 577–589 (Participantes card) -->
<div class="kpi-card">
  <div class="kpi-card__top">
    <span class="kpi-card__label">Participantes</span>
    <div class="kpi-card__icon" style="background:#eff6ff;color:#2563eb">
      <iconify-icon icon="lucide:users"></iconify-icon>
    </div>
  </div>
  <div class="kpi-card__value" id="stat-total">–</div>
  <div class="kpi-card__delta">
    <span class="kpi-chip kpi-chip--up" id="stat-total-chip" style="display:none"></span>
    <span id="stat-total-sub" style="color:var(--muted);font-size:12px"></span>
  </div>
</div>
```

**New card — to insert as 5th child of `.kpi-grid` (after line 627):**

```html
<div class="kpi-card" id="pending-meetings-card" style="display:none">
  <div class="kpi-card__top">
    <span class="kpi-card__label">Reuniões Pendentes</span>
    <div class="kpi-card__icon" style="background:rgba(244,63,94,0.08);color:#f43f5e">
      <iconify-icon icon="lucide:calendar-x"></iconify-icon>
    </div>
  </div>
  <div class="kpi-card__value" id="stat-pending" style="color:var(--danger)">–</div>
  <div class="kpi-card__delta">
    <span style="color:var(--muted);font-size:12px">turmas sem registro semanal</span>
  </div>
</div>
```

**CSS note:** `.kpi-grid` already has `repeat(4, 1fr)` — must change to `repeat(5, 1fr)` OR use `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))`. Safest: change to `repeat(5, 1fr)` only when card is visible. Alternatively render as `display:none` and toggle to `display:block` — grid will auto-expand since the element still occupies a grid cell when `display:block`.

**Wait:** `display:none` removes from flow. When showing, set `style=""` (remove display:none) so it enters the grid. The `repeat(4,1fr)` will become 5 columns naturally since the grid has `gap:20px` and no explicit column count constraint when 5 items exist — **actually it DOES have `repeat(4,1fr)` hardcoded** (line 221). Must update `.kpi-grid` CSS to `repeat(auto-fill, minmax(220px, 1fr))` OR change to `repeat(5, 1fr)`. Recommend: change inline via JS when showing, or change CSS to `auto-fill`.

**Animation:** Existing cards have nth-child animation delays (lines 232–235). New card is 5th child:
```css
.kpi-card:nth-child(5) { animation-delay: 0.25s; }
```

---

## 2. Exact JS Pattern — Fetch + Render KPI Stats

**File:** `frontend/index.html` (inline script)

### `apiFetch` helper (lines 836–846)
```js
async function apiFetch(url, mockFb) {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(4000) });
    if (!r.ok) throw new Error(r.status);
    isMock = false;
    return r.json();
  } catch {
    isMock = true;
    return mockFb();
  }
}
```

### `buildQs` — query string builder (lines 848–858)
```js
function buildQs(extra = {}) {
  const qs = new URLSearchParams();
  getSelectedGroupIds().forEach(id => qs.append('group_id', id));
  getSelectedPersonIds().forEach(id => qs.append('person_id', id));
  const df = document.getElementById('date-from').value;
  const dt = document.getElementById('date-to').value;
  if (df) qs.set('date_from', df);
  if (dt) qs.set('date_to',   dt);
  Object.entries(extra).forEach(([k,v]) => qs.set(k, v));
  return qs.toString() ? '?' + qs : '';
}
```

**Note:** For pending-meetings, `date_from`/`date_to` and `person_id` are irrelevant. Use `buildQs()` anyway for `group_id` pass-through to stay consistent — backend ignores unknown params.

### How KPI values are set (lines 1156–1166):
```js
document.getElementById('stat-total').textContent     = totalMembersCount || '–';
document.getElementById('stat-critical').textContent  = counts.critical + counts.warning;
document.getElementById('stat-qualified').textContent = activeData.filter(m => m.qualified).length;
```

### Pattern to follow for new card:
```js
async function loadPendingMeetings() {
  const qs = buildQs();  // picks up group_id filter
  const data = await apiFetch(`/api/pending-meetings${qs}`, () => ({ count: 0, groups: [] }));
  const card = document.getElementById('pending-meetings-card');
  if (!data.count || data.count === 0) {
    card.style.display = 'none';
    return;
  }
  card.style.display = '';          // enters the grid
  document.getElementById('stat-pending').textContent = data.count;
  // store for detail panel
  window._pendingMeetingsData = data.groups;
}
```

### Where to call it — `loadOverview` (lines 1013–1038):
```js
async function loadOverview() {
  showLoading(true);
  const qs = buildQs();
  const [absent, week, present, trend, heatmap] = await Promise.all([
    apiFetch(`/api/top-absent${qs}`,          () => MOCK.topAbsent()),
    apiFetch(`/api/attendance-by-week${qs}`,  () => MOCK.attendanceByWeek()),
    apiFetch(`/api/top-present${qs}`,         () => MOCK.topPresent()),
    apiFetch(`/api/attendance-trend${qs}`,    () => ({ ... })),
    apiFetch(`/api/person-week-heatmap${qs}`, () => ({ ... })),
  ]);
  // ... renders ...
  // ADD: loadPendingMeetings();  ← call after Promise.all resolves
}
```

### `refreshAll` (lines 1438–1444) already resets all tab state and re-calls loadTab — no change needed there; `loadOverview` will re-call `loadPendingMeetings` on every filter change.

---

## 3. Exact FastAPI Endpoint Patterns

**File:** `backend/main.py`

### Signature pattern — `group_id` list query param (lines 502–508):
```python
@app.get("/api/at-risk")
def at_risk(
    group_id: list[str] = Query(default=[]),
    alert_threshold: int = Query(3),
    inactive_threshold: int = Query(5),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]
    ...
```

### Active groups normalization (used in every endpoint):
```python
active_groups = [g for g in group_id if g and g != "all"]
```

### Filtering events by group (lines 514–516):
```python
eq = db.query(Event).order_by(Event.date)
if active_groups:
    eq = eq.filter(Event.group_id.in_(active_groups))
all_events = eq.all()
```

### New endpoint signature:
```python
@app.get("/api/pending-meetings")
def pending_meetings(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]
    ...
    return {"count": len(result), "groups": result}
```

### Response shape (follow `at-risk` style):
```python
# Return
{
  "count": 3,
  "groups": [
    {
      "id": "g1",
      "name": "Turma A",
      "missing_weeks": ["2025-12-02/2025-12-08", "2026-01-06/2026-01-12"]
    },
    ...
  ]
}
```

---

## 4. SQLAlchemy Query Patterns for Event Model

### Event model (models.py lines 18–23):
```python
class Event(Base):
    __tablename__ = "events"
    id       = Column(String, primary_key=True)
    date     = Column(DateTime)
    name     = Column(String)
    group_id = Column(String, index=True)
```

**Key:** `date` is `DateTime` (not `Date`). All comparisons must use `datetime` objects.

### Get all events ordered by date (pattern from lines 102–103):
```python
eq = db.query(Event).filter(Event.date >= cutoff).order_by(Event.date)
if active_groups:
    eq = eq.filter(Event.group_id.in_(active_groups))
events = eq.all()
```

### Get first event date per group (needed for D-04):
```python
from sqlalchemy import func

# One query: min date per group
rows = (
    db.query(Event.group_id, func.min(Event.date).label("first_date"))
    .group_by(Event.group_id)
)
if active_groups:
    rows = rows.filter(Event.group_id.in_(active_groups))
first_dates = {r.group_id: r.first_date for r in rows.all()}
```

### Date range filter for a specific week (Mon–Sun):
```python
# week_start = datetime of Monday 00:00:00
# week_end   = datetime of Sunday 23:59:59
events_in_week = db.query(Event).filter(
    Event.group_id == gid,
    Event.date >= week_start,
    Event.date <= week_end,
).first()  # just need existence check — .first() is faster than .all()
```

---

## 5. Week Calculation Logic (Python)

No existing week calculation in backend — must add fresh. Standard Python pattern:

```python
from datetime import datetime, timedelta, date

def get_monday(d: date) -> date:
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())  # weekday(): Mon=0, Sun=6

def week_range(monday: date):
    """Return (monday, sunday) for the week."""
    return monday, monday + timedelta(days=6)

def all_weeks_since(first_event_date: datetime, reference_sunday: date):
    """
    Yield (monday, sunday) for every Mon–Sun week from the week
    containing first_event_date up to and including reference_sunday's week.
    """
    start_monday = get_monday(first_event_date.date())
    ref_monday   = get_monday(reference_sunday)
    current = start_monday
    while current <= ref_monday:
        yield current, current + timedelta(days=6)
        current += timedelta(weeks=1)

def last_sunday(today: date) -> date:
    """
    Return the most recent Sunday (the end of the last complete week).
    If today IS Sunday, return today.
    """
    # weekday(): Mon=0 ... Sun=6
    days_since_sunday = (today.weekday() + 1) % 7  # 0 on Sunday, 1 on Monday…
    return today - timedelta(days=days_since_sunday)
```

**Alert trigger rule (D-02):** endpoint computes based on `last_sunday(date.today())`. No "only show on Sundays" gating — the API always returns current state; the frontend shows the card whenever count > 0.

---

## 6. Full Backend Logic Sketch

```python
from datetime import datetime, timedelta, date as date_type

@app.get("/api/pending-meetings")
def pending_meetings(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]

    # 1. Get all groups in scope
    gq = db.query(Group)
    if active_groups:
        gq = gq.filter(Group.id.in_(active_groups))
    groups = gq.all()
    if not groups:
        return {"count": 0, "groups": []}

    # 2. First event date per group
    feq = db.query(Event.group_id, func.min(Event.date).label("first_date")).group_by(Event.group_id)
    if active_groups:
        feq = feq.filter(Event.group_id.in_(active_groups))
    first_dates = {r.group_id: r.first_date for r in feq.all()}

    # 3. Reference point: last Sunday
    today = datetime.utcnow().date()
    days_since_sunday = (today.weekday() + 1) % 7
    ref_sunday = today - timedelta(days=days_since_sunday)

    # 4. All events (just dates) per group for range checks
    eq = db.query(Event.group_id, Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    # Build set of (group_id, monday_of_week) for quick lookup
    covered: set[tuple[str, date_type]] = set()
    for row in eq.all():
        d = row.date.date() if hasattr(row.date, 'date') else row.date
        monday = d - timedelta(days=d.weekday())
        covered.add((row.group_id, monday))

    # 5. Check each group
    result = []
    for g in groups:
        first = first_dates.get(g.id)
        if not first:
            continue  # group has no events at all — skip
        first_date = first.date() if hasattr(first, 'date') else first
        start_monday = first_date - timedelta(days=first_date.weekday())
        ref_monday   = ref_sunday - timedelta(days=ref_sunday.weekday())

        missing = []
        cur = start_monday
        while cur <= ref_monday:
            if (g.id, cur) not in covered:
                sun = cur + timedelta(days=6)
                missing.append(f"{cur.isoformat()}/{sun.isoformat()}")
            cur += timedelta(weeks=1)

        if missing:
            result.append({"id": g.id, "name": g.name, "missing_weeks": missing})

    return {"count": len(result), "groups": result}
```

---

## 7. Insertion Points — Exact Line Numbers

### `frontend/index.html`

| What | Where | Line |
|---|---|---|
| New KPI card HTML | After `</div>` closing 4th `.kpi-card` (Qualificados 3×) | After line 627 |
| CSS: `.kpi-grid` columns | Line 221: change `repeat(4, 1fr)` → `repeat(5, 1fr)` | 221 |
| CSS: 5th card animation | After `.kpi-card:nth-child(4)` rule (line 235) | After 235 |
| Detail panel div | After `.kpi-grid` closing `</div>` (line 628) | After 628 |

### `frontend/index.html` inline `<script>`

| What | Where | Line |
|---|---|---|
| `loadPendingMeetings()` function | After `loadMemberStatus` function (~line 1169) | ~1169 |
| Call `loadPendingMeetings()` | Inside `loadOverview()`, after `Promise.all` resolves | ~1035 |
| `window._pendingMeetingsData` store | Inside `loadPendingMeetings` | — |
| Click handler on `#pending-meetings-card` | Inside `init()` IIFE, after `initRiskPills()` | ~1503 |

### `backend/main.py`

| What | Where | Line |
|---|---|---|
| New imports (`date as date_type` already available via `datetime`) | Top of file (already: `from datetime import datetime, timedelta`) | 6 |
| New endpoint | After `@app.get("/api/dropouts")` block (~line 499) | After 499 |

---

## 8. Detail Panel Pattern

The closest existing pattern is `loadAlerts` / `alertCard` function (lines 1238–1250). For the expand/collapse inline panel, simplest approach matching project style:

```html
<!-- Inline below .kpi-grid — hidden by default -->
<div id="pending-detail-panel" style="display:none;margin-bottom:32px">
  <div class="chart-card">
    <div class="chart-card__header">
      <div>
        <div class="chart-card__title">Turmas com Reuniões Pendentes</div>
        <div class="chart-card__subtitle">Semanas sem registro desde o primeiro evento</div>
      </div>
      <button id="pending-detail-close" style="...">✕</button>
    </div>
    <div id="pending-detail-content"></div>
  </div>
</div>
```

Render pattern (follow `alertCard` at line 1241):
```js
function renderPendingDetail(groups) {
  const content = document.getElementById('pending-detail-content');
  content.innerHTML = `<ul class="alert-card__list">
    ${groups.map(g => `
      <li class="alert-card__item" style="flex-direction:column;align-items:flex-start;gap:4px">
        <span class="alert-card__name">${g.name}</span>
        <span class="alert-card__meta">${g.missing_weeks.join(' · ')}</span>
      </li>`).join('')}
  </ul>`;
}
```

---

## Common Pitfalls

### Pitfall 1: DateTime vs date comparison
**What goes wrong:** `Event.date` is `DateTime`. Comparing with Python `date` objects will fail silently or raise.
**Fix:** Always use `datetime` or call `.date()` on the value: `first.date() if hasattr(first, 'date') else first`

### Pitfall 2: `repeat(4, 1fr)` hard-coded in CSS
**What goes wrong:** 5th card wraps to a new row if grid is fixed at 4 columns.
**Fix:** Change to `repeat(5, 1fr)` in CSS, or use `repeat(auto-fill, minmax(220px, 1fr))` for responsiveness. Also update `@media (max-width: 900px)` rule (line 469) which sets `repeat(2, 1fr)` — that remains correct.

### Pitfall 3: UTC vs local dates
**What goes wrong:** `datetime.utcnow()` may return a different date than the server's local "Sunday". All existing code uses `datetime.utcnow()` (e.g. lines 47, 98). Stay consistent — use UTC throughout.

### Pitfall 4: Groups with no events at all
**What goes wrong:** `first_dates.get(g.id)` returns `None` → crash when computing weeks.
**Fix:** `if not first: continue` guard (shown in logic sketch above).

### Pitfall 5: `display:none` card occupies no grid column
**What goes wrong:** Setting card to `display:none` makes the grid stay at 4 columns visually even after show.
**Fix:** Toggle `display` between `'none'` and `''` (empty string = restore to default block).

---

## Environment Availability

Step 2.6: SKIPPED — phase is code-only changes to existing Python/JS files. No new external dependencies.

---

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | None detected in repo |
| Config file | None |
| Quick run command | Manual: `curl http://localhost:8000/api/pending-meetings` |
| Full suite command | Manual endpoint smoke test |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Command |
|---|---|---|---|
| D-01/D-02 | Correct Mon–Sun week boundary | unit | Python REPL: verify `get_monday()` and `last_sunday()` |
| D-03 | Any event row counts as registered | smoke | Insert test event, verify week disappears from missing |
| D-04 | All weeks from first event checked | smoke | `curl /api/pending-meetings` — verify old gaps appear |
| D-07 | Card hidden when count=0 | manual | Filter to group with no gaps, verify card absent |
| D-09 | Click shows detail | manual | Click card, verify detail panel opens |

### Wave 0 Gaps
- No test infrastructure exists — all verification is manual smoke testing and visual inspection.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `backend/main.py` — all endpoint patterns, query patterns, DB session usage
- `backend/models.py` — Event model schema
- `frontend/index.html` — KPI card HTML, CSS classes, inline JS patterns
- `frontend/app.js` — `fetchJSON` pattern (simpler than inline script; inline script uses `apiFetch`)

### Notes
- `app.js` (the standalone file) is a **simpler older version** of the dashboard JS. The real production code is the inline `<script>` block inside `index.html` (lines 786–1513). The planner should target `index.html`, not `app.js`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | UTC dates from DB align with local "Sunday" intent | Week Calculation | Could check wrong week boundary if server is in different TZ |
| A2 | Groups with zero events should be silently skipped (not flagged as all-weeks-pending) | Backend Logic | If wrong, groups never started would spam alerts |

A2 is inferred from D-04: "check ALL weeks from group's first event" — a group with no events has no first event, so no weeks to check.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — direct file read
- Architecture: HIGH — direct file read
- Pitfalls: HIGH — inferred from existing code patterns and Python datetime behavior

**Research date:** 2026-05-12
**Valid until:** Until `frontend/index.html` or `backend/main.py` is significantly restructured
