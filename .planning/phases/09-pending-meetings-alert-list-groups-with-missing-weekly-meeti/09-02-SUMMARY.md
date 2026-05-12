---
phase: 09-pending-meetings-alert-list-groups-with-missing-weekly-meeti
plan: "02"
subsystem: frontend
tags: [kpi-card, pending-meetings, detail-panel, css, html, js]
dependency_graph:
  requires: ["09-01"]
  provides: ["pending-meetings-ui"]
  affects: ["frontend/index.html"]
tech_stack:
  added: []
  patterns: [toggle-panel, apiFetch, buildQs]
key_files:
  modified: ["frontend/index.html"]
decisions:
  - ".kpi-grid changed to repeat(5,1fr); responsive override at max-width:900px untouched"
  - "Card hidden by default (display:none); shown only when API returns count > 0"
  - "Detail panel outside kpi-grid; toggled via click on card, closed via ✕ button"
metrics:
  duration: "~10 min"
  completed: "2026-05-12"
---

# Phase 09 Plan 02: Pending Meetings KPI Card + Detail Panel Summary

**One-liner:** 5th KPI card wired to `/api/pending-meetings` with toggleable inline group detail panel.

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | CSS: kpi-grid → repeat(5,1fr); add nth-child(5) delay | 56ce853 |
| 2 | HTML+JS: card, detail panel, loadPendingMeetings(), renderPendingDetail(), click handlers | 56ce853 |

## Edit Locations

| Change | File | Line (post-edit) |
|--------|------|-----------------|
| `.kpi-grid` columns | `frontend/index.html` | 221 |
| `.kpi-card:nth-child(5)` animation | `frontend/index.html` | 236 |
| 5th KPI card HTML | `frontend/index.html` | ~628 |
| `#pending-detail-panel` HTML | `frontend/index.html` | ~642 |
| `loadPendingMeetings()` definition | `frontend/index.html` | 1200 |
| `renderPendingDetail()` definition | `frontend/index.html` | ~1218 |
| `await loadPendingMeetings()` call | `frontend/index.html` | 1065 |
| Click handlers in init IIFE | `frontend/index.html` | ~1530 |

## Verification Results

```
repeat(5, 1fr)      → line 221 (exactly 1 match) ✓
nth-child(5)        → line 236 (exactly 1 match) ✓
pending-meetings-card count: 3 ✓
pending-detail-panel count:  4 ✓
stat-pending count:          2 ✓
loadPendingMeetings count:   2 (definition + call) ✓
renderPendingDetail count:   2 (definition + call) ✓
```

## Deviations from Plan

None — plan executed exactly as written. Change 4 used the fixed single-toggle version with both card click + close button handlers as specified.

## Known Stubs

None — card hides itself when API returns count=0 (mock fallback), no placeholder text shown.

## Threat Flags

None beyond plan's documented T-09-04 (innerHTML injection of group names from internal DB — accepted).
