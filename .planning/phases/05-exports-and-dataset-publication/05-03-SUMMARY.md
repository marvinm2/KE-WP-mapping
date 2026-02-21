---
phase: 05-exports-and-dataset-publication
plan: 03
subsystem: ui
tags: [flask, jinja2, downloads, gmt, turtle, rdf, zenodo, doi, navbar, context-processor]

# Dependency graph
requires:
  - phase: 05-exports-and-dataset-publication
    plan: 01
    provides: generate_ke_wp_gmt, generate_ke_go_gmt, generate_ke_wp_turtle, generate_ke_go_turtle exporter functions

provides:
  - GET /downloads — public downloads page with 4 format cards and optional DOI citation block
  - GET /exports/gmt/ke-wp — KE-WP GMT download (cache-then-serve, optional min_confidence param)
  - GET /exports/gmt/ke-go — KE-GO GMT download (cache-then-serve, optional min_confidence param)
  - GET /exports/rdf/ke-wp — KE-WP Turtle download (cache-then-serve)
  - GET /exports/rdf/ke-go — KE-GO Turtle download (cache-then-serve)
  - templates/downloads.html — standalone page with 2-column grid export cards
  - inject_zenodo_meta() context processor — DOI available in all templates
  - Downloads nav link in navigation.html
  - Export Formats section in stats.html

affects:
  - 05-04 (DOI badge wiring now in place; publish flow writes to zenodo_meta.json which context processor reads)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Cache-then-serve pattern for on-demand file generation (static/exports/ as file cache)
    - Global context processor for zenodo_meta so navbar DOI badge works on every page
    - Module-level EXPORT_CACHE_DIR = Path('static/exports') constant shared by all route handlers

key-files:
  created:
    - templates/downloads.html
    - static/exports/.gitkeep
  modified:
    - src/blueprints/main.py
    - templates/components/navigation.html
    - templates/stats.html
    - app.py

key-decisions:
  - "EXPORT_CACHE_DIR = Path('static/exports') as module constant — shared by all four download routes and the GMT helper"
  - "inject_zenodo_meta() context processor in app.py — data/zenodo_meta.json read once per request, empty dict returned on missing file; avoids per-route boilerplate"
  - "GMT generation wrapped in _get_or_generate_gmt() helper — date-stamped filenames mean each new day regenerates automatically without manual cache invalidation"
  - "cache_model passed through set_main_models so WikiPathways SPARQL responses are cached across GMT generation calls"

patterns-established:
  - "Download routes return 503 with JSON error body when cache file is empty (no data) — consistent with API error pattern"
  - "Per-day filename stamping (YYYY-MM-DD) for GMT cache files — stale files accumulate but are cheap; future cleanup cron can prune old dates"

requirements-completed: [EXPRT-01, EXPRT-02, EXPRT-03]

# Metrics
duration: 5min
completed: 2026-02-21
---

# Phase 05 Plan 03: Download Routes and Downloads Page Summary

**Flask download routes wired to Plan 01 exporters with on-demand file caching, /downloads page with 4 format cards, DOI badge in navbar via global context processor, and export buttons on /stats**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-21T19:23:05Z
- **Completed:** 2026-02-21T19:28:05Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Five new public routes: `/downloads` page + four `/exports/*` file download endpoints wired to `gmt_exporter.py` and `rdf_exporter.py`
- On-demand cache-then-serve pattern: GMT/Turtle files generated on first request, written to `static/exports/`, subsequent requests serve cached file directly
- `inject_zenodo_meta()` context processor adds `zenodo_meta` dict globally so navbar renders DOI badge on every page as soon as `data/zenodo_meta.json` has a `doi` field
- `/downloads` page with four export cards (KE-WP GMT, KE-GO GMT, KE-WP Turtle, KE-GO Turtle), confidence-filtered GMT download links, DOI citation block, and data-sources section
- `/stats` page augmented with Export Formats section linking to all four download routes

## Task Commits

Each task was committed atomically:

1. **Task 1: Public export download routes in main.py and static/exports/.gitkeep** - `22a695a` (feat)
2. **Task 2: downloads.html page, navbar DOI badge, and stats.html download links section** - `21f5529` (feat)

**Plan metadata:** (committed after SUMMARY.md)

## Files Created/Modified

- `src/blueprints/main.py` — Added `EXPORT_CACHE_DIR`, `cache_model_ref` global, updated `set_models()` with `cache_model` param, added `downloads()` route, `_get_or_generate_gmt()` helper, four export download routes
- `templates/downloads.html` — New standalone page: 4 format cards in CSS grid, DOI citation block, note/data-sources sections
- `static/exports/.gitkeep` — Empty file ensuring `static/exports/` exists in git for cache dir
- `templates/components/navigation.html` — Added Downloads nav link; added DOI badge div in title section reading `zenodo_meta.doi`
- `templates/stats.html` — Added Export Formats section with 4 download buttons and link to /downloads
- `app.py` — Added `inject_zenodo_meta()` context processor; updated `set_main_models` call to pass `cache_model`

## Decisions Made

- `EXPORT_CACHE_DIR = Path('static/exports')` as module-level constant — all four routes and the GMT helper share it; avoids repeating the path
- `inject_zenodo_meta()` global context processor — reads `data/zenodo_meta.json` once per request; returns `{}` on missing/invalid file; means navbar DOI badge requires zero per-route changes
- GMT filenames include ISO date (`KE-WP_YYYY-MM-DD_All.gmt`) — natural daily cache invalidation without explicit TTL logic
- `cache_model` threaded through `set_main_models` — WikiPathways SPARQL responses cached across repeated GMT download calls; consistent with existing cache pattern in api_bp

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All four download routes functional; `/downloads` page live
- DOI badge in navbar ready to display as soon as Phase 05-02 Zenodo publish writes `data/zenodo_meta.json` with a `doi` field
- GMT generation live and caching to `static/exports/` on demand
- All 66 existing tests pass; no regressions

---
*Phase: 05-exports-and-dataset-publication*
*Completed: 2026-02-21*
