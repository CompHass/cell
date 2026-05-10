# 06-03 Summary — app.js Filter Wiring

**Status:** Complete  
**Files modified:** `frontend/app.js`

## What was done
- `loadDashboard(filters={})` now accepts filters object instead of groupId string
- `getFilters()` helper reads all 4 DOM inputs (group, date-from, date-to, person-name)
- `URLSearchParams` used for safe query string construction
- "Filtrar" button triggers `loadDashboard(getFilters())`
- Group select change also triggers `loadDashboard(getFilters())`
- DOMContentLoaded calls `loadDashboard(getFilters())` (unfiltered on load)

## Verification
- All key patterns present in app.js: `date-from`, `date_from`, `person_name`, `apply-filters`, `getFilters`, `URLSearchParams`
- End-to-end API tests passing with all filter combinations
