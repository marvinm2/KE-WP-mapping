---
plan_id: 26-07
plan: "07"
phase: 26-public-api-and-exports
title: "Explore page — 4th Reactome tab with AJAX DataTable"
status: partial-checkpoint
subsystem: frontend
tags: [explore, datatable, reactome, ui]
requires:
  - 26-05 (GET /api/v1/reactome-mappings — list/single endpoints already shipped)
  - 26-06 (Reactome model wired into main blueprint set_models — needed for reactome_mapping_model)
provides:
  - 4th explore tab with AJAX-driven DataTable backed by /api/v1/reactome-mappings
  - reactome_count context var on /explore route
  - 4-way tab switcher (wp / go / reactome / gaps) with independent filter state per tab
affects:
  - templates/explore.html (4-way tab switcher; new #reactome-explore-content block)
  - src/blueprints/main.py (explore route adds reactome_count kwarg)
key-files:
  modified:
    - src/blueprints/main.py
    - templates/explore.html
decisions:
  - Reused /get_aop_options endpoint to populate the Reactome AOP Select2 (cheap second fetch instead of caching client-side, mirrors gaps tab pattern)
  - Reactome filter wiring lives in window.* helpers (clearReactomeAopFilter, etc.) for parity with the existing WP clear* helpers used by inline onclick handlers in filter chips
metrics:
  tasks_completed: 2
  tasks_total: 3 (1 checkpoint remaining)
  duration_minutes: ~12
---

# Phase 26 Plan 07: Explore — 4th Reactome tab with AJAX DataTable Summary (PARTIAL — checkpoint pending)

One-liner: Adds a Reactome tab to the explore page with an AJAX-driven DataTable that consumes /api/v1/reactome-mappings, parallel filter UI, and a 4-way tab switcher; **awaiting human visual verification**.

## Status

**Auto tasks 1 + 2 complete.** Plan paused at the `checkpoint:human-verify` (blocking gate). The orchestrator must run the dev server and walk through the verify steps in the browser before this plan can be marked done.

## Completed Tasks

| Task | Name                                                                   | Commit  | Files                                            |
| ---- | ---------------------------------------------------------------------- | ------- | ------------------------------------------------ |
| 1    | Pass reactome_count into explore template context                       | a064f66 | src/blueprints/main.py                           |
| 2    | Add Reactome tab button + content block + filter chips to explore.html  | d405a17 | templates/explore.html                           |

## What Was Built

### Task 1 — Backend context wiring (src/blueprints/main.py)

The `/explore` route handler now computes `reactome_count` from `reactome_mapping_model.get_all_mappings()`, defends against a missing model with a `0` fallback, and threads the value into both the success and error `render_template` calls. Done criteria: `grep -c "reactome_count" src/blueprints/main.py` returns 5; `grep -c "reactome_count="` returns 2.

### Task 2 — Frontend Reactome tab (templates/explore.html)

Three coordinated edits:

1. **Tab switcher** — 4th button inserted between GO and Coverage Gaps. Tab order is exactly `wp → go → reactome → gaps` per D-16. Label is `KE-Reactome Mappings ({{ reactome_count }})`.
2. **Content block** — New `#reactome-explore-content` div mirrors the WP block: AOP Select2 filter, confidence toggle buttons, active-filter chips, and a `#reactomeDatasetTable` with **8 columns** (KE ID, KE Title, Reactome ID, Pathway Name, Confidence, Proposer, Curator, Approved). **No Actions column** (D-14 — Reactome v1 does not support Propose Change).
3. **JavaScript** — Three additions:
   - `var reactomeState = { aopId, aopLabel, confidence }` and `reactomeTableInitialized = false` flag near the existing GO state.
   - 4-way tab switcher: every branch now also hides `#reactome-explore-content`, and the new `else if (tab === 'reactome')` branch lazy-initialises the DataTable with `serverSide: true` and a custom `ajax` callback that fetches `/api/v1/reactome-mappings?page=…&per_page=…&aop_id=…&confidence_level=…` and re-shapes the JSON response into DataTables' draw/recordsTotal/data envelope.
   - Filter wiring: `renderReactomeFilterChips()`, `clearReactomeAopFilter`, `clearReactomeConfidenceFilter`, `clearReactomeAllFilters`, `applyReactomeFilters` (all mirroring the existing WP helpers but namespaced); a second fetch of `/get_aop_options` populates `#reactome-aop-filter-select`; jQuery `change` and `click` handlers on the AOP select and confidence buttons update `reactomeState` and `ajax.reload()` the table.

The Reactome ID column uses a custom render function that builds an anchor pointing to `https://reactome.org/PathwayBrowser/#/<id>`. Reactome IDs are validated upstream (Phase 23 enforces `^R-HSA-[0-9]+$`), so the value is safe to interpolate as both anchor href and text. Proposer / Curator columns strip the `provider:` prefix from the provenance strings, matching the WP tab.

## Acceptance Criteria — All Pass

| # | Criterion                                                                                       | Result |
| - | ----------------------------------------------------------------------------------------------- | ------ |
| 1 | `grep -c 'data-tab="reactome"' templates/explore.html` == 1                                     | 1 ✓    |
| 2 | `grep -c 'id="reactome-explore-content"' templates/explore.html` == 1                            | 1 ✓    |
| 3 | `grep -c 'id="reactomeDatasetTable"' templates/explore.html` == 1                                | 1 ✓    |
| 4 | `grep -c 'fetch.*/api/v1/reactome-mappings' templates/explore.html` == 1                        | 1 ✓    |
| 5 | `grep -c 'reactome\.org/PathwayBrowser/#/' templates/explore.html` == 1                          | 1 ✓    |
| 6 | `grep -c 'reactomeTableInitialized' templates/explore.html` >= 2                                | 4 ✓    |
| 7 | `grep -c 'var reactomeState' templates/explore.html` == 1                                       | 1 ✓    |
| 8 | `grep -c "tab === 'reactome'" templates/explore.html` == 1                                      | 1 ✓    |
| 9 | No `<th>Actions</th>` inside `#reactome-explore-content`                                        | 0 ✓    |

Jinja2 template parses cleanly (`from jinja2 import Environment, FileSystemLoader; env.get_template('explore.html')` raises no error).

## Pending Checkpoint — Human Verification (blocking)

The plan's third task is `<task type="checkpoint:human-verify" gate="blocking">`. Sandbox cannot reliably run `python app.py &` and a browser, so the orchestrator must perform the verification steps below. Verbatim from the plan:

1. Kill any running dev server: `pkill -f "python.*app.py"`
2. Start dev server: `python app.py &` (port 5000)
3. Open http://localhost:5000/explore in a browser. Verify:
   - Tab switcher shows 4 buttons in order: WP, GO, Reactome, Coverage Gaps
   - The Reactome tab label includes a count, e.g. "KE-Reactome Mappings (N)" where N matches the number of approved Reactome mappings in the DB
4. Click the Reactome tab. Verify:
   - The other three content blocks are hidden; only `#reactome-explore-content` is visible
   - The DataTable loads (network tab shows fetch to `/api/v1/reactome-mappings`)
   - 8 columns display: KE ID, KE Title, Reactome ID, Pathway Name, Confidence, Proposer, Curator, Approved
   - No "Actions" column present
   - Reactome ID values are clickable and open `https://reactome.org/PathwayBrowser/#/R-HSA-XXX` in a new tab
   - Proposer / Curator strings show the username only (no `github:` / `orcid:` prefix)
5. Test filters:
   - Select an AOP from the AOP filter dropdown → table reloads with only matching KEs
   - Click "High" confidence button → table narrows to High-confidence rows
   - Switch back to WP tab and back to Reactome tab → Reactome filter state persists; WP filter state was unchanged
6. Test pagination:
   - Bottom of table: page-size selector + page navigation work; URL params show page/per_page
7. Test 4-way switcher:
   - Click each tab in turn (WP → GO → Reactome → Gaps → WP); only one content block is visible at a time
8. Kill the dev server: `pkill -f "python.*app.py"`

Resume signal: type "approved" or describe issues (specifying which step failed).

## Deviations from Plan

None — both auto tasks executed exactly as written. No bugs found, no missing functionality, no architectural questions.

## Self-Check: PASSED

- src/blueprints/main.py: FOUND (commit a064f66 modifies it)
- templates/explore.html: FOUND (commit d405a17 modifies it)
- Commit a064f66: FOUND in git log
- Commit d405a17: FOUND in git log
- All 9 acceptance criteria: PASS
- Jinja2 parses: PASS
