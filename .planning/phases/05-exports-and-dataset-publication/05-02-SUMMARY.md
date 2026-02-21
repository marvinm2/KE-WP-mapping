---
phase: 05-exports-and-dataset-publication
plan: 02
subsystem: api
tags: [zenodo, doi, export, gmt, turtle, rdf, admin]

# Dependency graph
requires:
  - phase: 05-01
    provides: gmt_exporter.py and rdf_exporter.py modules used in regenerate_exports route

provides:
  - src/exporters/zenodo_uploader.py with zenodo_publish() and _build_zenodo_metadata()
  - POST /admin/exports/regenerate — clears and rebuilds all GMT + Turtle cache files
  - POST /admin/exports/publish-zenodo — uploads cached exports to Zenodo, persists DOI
  - data/zenodo_meta.json — persistent deposition_id and doi state file

affects: [05-03-downloads-page, future Zenodo versioning]

# Tech tracking
tech-stack:
  added: [requests (Zenodo REST API via PUT bucket upload)]
  patterns: [Admin-only POST endpoint returning JSON status; persistent JSON state file for external service IDs]

key-files:
  created:
    - src/exporters/zenodo_uploader.py
    - data/zenodo_meta.json
  modified:
    - src/blueprints/admin.py
    - app.py
    - .env.example
    - .gitignore

key-decisions:
  - "data/zenodo_meta.json unignored from .gitignore — it is persistent state (small), not a large pre-computed file like ke_metadata.json"
  - "Zenodo bucket PUT API used (not deprecated /files POST) — current Zenodo recommendation for file uploads"
  - "publish_zenodo returns 503 with clear message when ZENODO_API_TOKEN missing — does not crash"
  - "regenerate_exports loops over four confidence levels (All/High/Medium/Low) producing named GMT files for each"

patterns-established:
  - "Admin route pattern: import exporter modules inline inside route function to avoid circular imports"
  - "External service ID persistence: read from data/*.json on each call, write back after success"

requirements-completed: [EXPRT-04]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 5 Plan 02: Admin Export Regeneration and Zenodo Publish Routes Summary

**Zenodo deposit workflow (first-publish + new-version) wired to admin endpoints that rebuild GMT/Turtle cache and publish the dataset with persistent DOI storage in data/zenodo_meta.json**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T19:17:04Z
- **Completed:** 2026-02-21T19:20:27Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created `src/exporters/zenodo_uploader.py` standalone module (no Flask imports) implementing first-publish and new-version workflows via Zenodo bucket PUT API
- Added `POST /admin/exports/regenerate` — clears `static/exports/`, regenerates four confidence-level GMT files for KE-WP and KE-GO plus full Turtle exports, returns JSON file list
- Added `POST /admin/exports/publish-zenodo` — reads cached export files, calls `zenodo_publish()`, writes DOI and deposition_id back to `data/zenodo_meta.json`
- Extended `set_models()` signature with `go_mapping` and `cache_model` params; updated `app.py` call accordingly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create zenodo_uploader.py** - `a17bc34` (feat)
2. **Task 2: Admin routes, zenodo_meta.json, .env.example** - `f2cad0f` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `src/exporters/zenodo_uploader.py` - Zenodo deposit and new-version workflow using requests
- `data/zenodo_meta.json` - Persistent DOI and deposition_id storage (initial null state)
- `src/blueprints/admin.py` - Two new admin routes and extended set_models() signature
- `app.py` - Updated set_admin_models() call with go_mapping and cache_model
- `.env.example` - ZENODO_API_TOKEN documented with Zenodo Dashboard instructions
- `.gitignore` - Exception added to unignore data/zenodo_meta.json

## Decisions Made
- `data/zenodo_meta.json` unignored in `.gitignore` — the `data/*.json` pattern existed for large pre-computed files; `zenodo_meta.json` is a small persistent state file that must be tracked
- Zenodo bucket PUT API used (not deprecated /files POST endpoint) — current Zenodo recommendation
- `publish_zenodo` returns 503 with clear message when `ZENODO_API_TOKEN` missing — does not crash
- Import of exporter modules kept inline inside route functions to avoid circular imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Unignored data/zenodo_meta.json from .gitignore**
- **Found during:** Task 2 (creating data/zenodo_meta.json)
- **Issue:** `data/*.json` pattern in .gitignore blocked `git add data/zenodo_meta.json` — commit would have silently omitted the initial state file
- **Fix:** Added `!data/zenodo_meta.json` exception line to .gitignore directly below the `data/*.json` rule
- **Files modified:** .gitignore
- **Verification:** `git add data/zenodo_meta.json` succeeded after fix; file included in commit f2cad0f
- **Committed in:** f2cad0f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to include the persistent DOI state file in version control. No scope creep.

## Issues Encountered
- None beyond the .gitignore deviation above.

## User Setup Required

External services require manual configuration before `POST /admin/exports/publish-zenodo` works:

1. Create a Zenodo account at https://zenodo.org/signup/ (use https://sandbox.zenodo.org for testing first)
2. Go to Zenodo Dashboard -> Settings -> Applications -> Personal access tokens
3. Create a new token with the `deposit:write` scope
4. Add to `.env`: `ZENODO_API_TOKEN=<your-token>`

No other external configuration required.

## Next Phase Readiness
- Plan 03 can now surface the DOI badge in the downloads page navbar and wire the admin panel buttons to the two new endpoints
- `data/zenodo_meta.json` is in git and will persist the DOI across restarts once a first publish completes

---
*Phase: 05-exports-and-dataset-publication*
*Completed: 2026-02-21*
