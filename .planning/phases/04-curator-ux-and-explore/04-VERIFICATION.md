---
phase: 04-curator-ux-and-explore
verified: 2026-02-21T17:34:45Z
status: human_needed
score: 12/12 must-haves verified
re_verification: false
human_verification:
  - test: "Select a KE from the dropdown on http://localhost:5000 and observe the context panel"
    expected: "A collapsible <details> panel appears with KE title prominently in summary, biolevel badge, description, AOP membership list (or 'No AOP membership found for this KE.'), and 'View on AOP-Wiki' link. Clicking the summary line collapses the panel. Browser Network tab shows /api/ke_detail/ called, NOT /api/ke_context/"
    why_human: "Panel insertion uses jQuery DOM manipulation — cannot verify DOM render or visual layout from code alone"
  - test: "Visit http://localhost:5000/?ke_id=KE%2055"
    expected: "KE 55 is pre-selected in the KE dropdown and the context panel auto-loads without manual selection"
    why_human: "URL param pre-fill depends on Select2 initialization timing (100ms setTimeout) — browser timing cannot be verified statically"
  - test: "Visit http://localhost:5000/explore, select an AOP from the AOP filter, then click High confidence"
    expected: "KE-WP table reloads via AJAX (empty tbody in source, rows populated by DataTables). AOP chip and Confidence chip both appear above table. Clicking x on a chip removes that filter. Clear all removes both."
    why_human: "Filter chips rendered via jQuery DOM manipulation; AJAX table loading requires live browser execution"
  - test: "Switch to Coverage Gaps tab, select any AOP"
    expected: "Table loads with KE ID, KE Title, Biological Level, and Map button for each unmapped KE. Clicking Map navigates to /?ke_id=KE%20NNN"
    why_human: "Gap computation depends on runtime cross-reference between /get_aop_kes/ and /api/v1/mappings — cannot verify result set statically"
  - test: "Visit http://localhost:5000/stats without being logged in (or in incognito)"
    expected: "Page loads (200, no redirect). Three metric cards show numeric counts. Confidence breakdown table shows High/Medium/Low rows. Select an AOP — AOP coverage indicator appears. Download CSV button downloads a CSV file."
    why_human: "Metric card values depend on live DB state; coverage indicator and export link update require browser JS execution"
---

# Phase 4: Curator UX and Explore Verification Report

**Phase Goal:** Curators can efficiently navigate the mapping database, see which KEs still need coverage, and filter approved mappings by AOP, confidence, and other dimensions; dataset metrics are visible at a glance
**Verified:** 2026-02-21T17:34:45Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `data/ke_aop_membership.json` exists and maps KE labels to lists of AOP objects | VERIFIED | File exists with 1,567 KE keys; sample: `'KE 142': [{'aop_id': 'AOP 1', 'aop_title': '...'}]` |
| 2 | `ServiceContainer` exposes `ke_aop_membership` and `ke_metadata_index` lazy properties | VERIFIED | Both properties implemented at lines 144-172 of `src/services/container.py`; `__init__` sets `_ke_aop_membership = None` and `_ke_metadata_index = None` |
| 3 | `GET /api/ke_detail/<ke_id>` returns title, description, biolevel, ke_page, and aop_membership from local data with no SPARQL | VERIFIED | Endpoint at line 273 of `api.py` reads from module-level `ke_metadata` + `ke_aop_membership` — no SPARQL call. All 6 fields returned. |
| 4 | Selecting a KE shows a unified collapsible panel with title, description, AOP membership, biolevel badge, and AOP-Wiki link | VERIFIED (code) | `loadKEDetail()` at line 1130, `renderKEContextPanel()` at line 1147, `removeKEContextPanel()` at line 1142 all exist and are substantive in `static/js/main.js`; panel is a `<details>` element with `open` attribute |
| 5 | Panel auto-loads on KE selection; no manual trigger required | VERIFIED (code) | `handleKESelection()` calls `this.loadKEDetail(keId)` at line 1104; $.getJSON fetch is automatic |
| 6 | URL param `?ke_id=` pre-fills KE dropdown after Select2 initializes | VERIFIED (code) | `this.preselectedKE` set in `init()` at line 117; applied via `setTimeout()` in `populateKEDropdown()` at line 367-369 |
| 7 | Explore page KE-WP Mappings tab is AJAX-driven DataTable with AOP (Select2) and confidence (toggle) filters | VERIFIED (code) | `serverSide: true` at line 270 of `explore.html`; `#aop-filter-select` Select2 at line 369; `#confidence-filter-btns` at line 113; `#active-filter-chips` at line 122; WP `<tbody>` is empty |
| 8 | Active filters appear as removable chips; filters combine with AND logic | VERIFIED (code) | `renderFilterChips()` at line 316 of `explore.html`; both `wpState.aopId` and `wpState.confidence` are applied simultaneously in `applyWpFilters()` which calls `wpTable.ajax.reload()` |
| 9 | Coverage Gaps tab shows unmapped KEs per AOP; Map button deep-links to `/?ke_id=` | VERIFIED (code) | `loadCoverageGaps()` at line 410; Map button href `/?ke_id=${encodedKe}` at line 473 of `explore.html`; three-tab structure confirmed at lines 85-95 |
| 10 | `GET /stats` is publicly accessible (no `@login_required`) and shows metric cards, confidence breakdown | VERIFIED | Route at line 506 of `main.py` has no `@login_required` decorator; `stats.html` renders `{{ stats.wp_total }}`, `{{ stats.go_total }}`, `{{ stats.total }}`, and a `High/Medium/Low` confidence loop |
| 11 | AOP coverage indicator appears when AOP is selected on /stats | VERIFIED (code) | `updateAopCoverage()` in `stats.html` at line 176 calls `/get_aop_kes/` + `/api/v1/mappings?aop_id=` and sets `#aop-coverage-indicator` text; element hidden by default via `style="display:none;"` |
| 12 | `?format=csv` on `/api/v1/mappings` returns CSV content | VERIFIED | `format_param = request.args.get("format", "").lower()` at line 149 of `v1_api.py`; `if format_param == "csv": use_csv = True` at line 150-151; backward-compatible with `Accept: text/csv` header |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/precompute_ke_aop_membership.py` | SPARQL precompute writing `data/ke_aop_membership.json` | VERIFIED | 106 lines; `json.dump()` at line 94; writes to `data/ke_aop_membership.json` |
| `data/ke_aop_membership.json` | KE-to-AOP membership data (>100 KEs) | VERIFIED | 1,567 KE keys, each with list of `{aop_id, aop_title}` dicts |
| `src/services/container.py` | `ke_aop_membership` and `ke_metadata_index` lazy properties | VERIFIED | Both properties at lines 144-172; both `_` attrs in `__init__` at lines 50-51 |
| `src/blueprints/api.py` | `GET /api/ke_detail/<ke_id>` endpoint; `ke_aop_membership` global | VERIFIED | Endpoint at line 273; global at line 49; `set_models()` accepts `ke_aop_membership_data` param |
| `static/js/main.js` | `loadKEDetail()`, `renderKEContextPanel()`, `removeKEContextPanel()`, URL param pre-fill | VERIFIED | All four elements confirmed at lines 1104, 1130, 1142, 1147, 117-120, 367-370 |
| `static/css/main.css` | `.ke-context-title`, `.filter-chip`, `.filter-chip-remove`, `.filter-chips-clear` | VERIFIED | All classes present at lines 1154, 1183, 1192, 1205, 1220 |
| `templates/explore.html` | AJAX DataTable, AOP Select2, confidence toggle, filter chips, Coverage Gaps tab | VERIFIED | All structural elements confirmed: `serverSide: true`, `#aop-filter-select`, `#confidence-filter-btns`, `#active-filter-chips`, `#gaps-explore-content`, `gapsTable`, Map button href |
| `src/blueprints/main.py` | `get_mapping_stats()` helper + `/stats` route (no `@login_required`) | VERIFIED | Helper at line 35; route at line 506; no login decorator; Stats link in navigation at `templates/components/navigation.html` line 13 |
| `templates/stats.html` | Metric cards, confidence breakdown, AOP filter, export buttons, coverage indicator | VERIFIED | 205 lines; all required elements confirmed; `#aop-coverage-indicator` hidden by default |
| `src/blueprints/v1_api.py` | `?format=csv` param support in `_respond_collection` | VERIFIED | `format_param = request.args.get("format", "").lower()` at line 149; CSV branch at lines 150-151 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/precompute_ke_aop_membership.py` | `data/ke_aop_membership.json` | `json.dump()` | WIRED | `json.dump(membership, f, ...)` at line 94 of script |
| `src/services/container.py` ke_aop_membership | `data/ke_aop_membership.json` | `open(path)` | WIRED | `os.path.join(PROJECT_ROOT, 'data', 'ke_aop_membership.json')` at line 148 |
| `src/blueprints/api.py` | `ke_aop_membership` module var | `set_models()` injection | WIRED | `ke_aop_membership_data` param at line 54; assigned at line 68; `app.py` passes `ke_aop_membership_data=services.ke_aop_membership` at line 114 |
| `api.py get_ke_detail` | `ke_aop_membership.get(ke_id, [])` | direct use | WIRED | Line 295: `ke_aop_membership.get(ke_id, []) if ke_aop_membership else []` |
| `static/js/main.js handleKESelection()` | `/api/ke_detail/<ke_id>` | `$.getJSON()` in `loadKEDetail()` | WIRED | Line 1133: `$.getJSON('/api/ke_detail/${encodedKeId}')` |
| `static/js/main.js init()` | `populateKEDropdown()` callback | `this.preselectedKE` stored then applied | WIRED | Lines 117-120 store param; lines 367-370 apply after Select2 ready |
| `templates/explore.html DataTable ajax` | `/api/v1/mappings` | `fetch()` with params | WIRED | Line 279: `fetch('/api/v1/mappings?' + params.toString(), ...)` |
| `templates/explore.html gaps tab` | `/get_aop_kes/<aop_id>` | `$.getJSON()` | WIRED | Line 413: `$.getJSON('/get_aop_kes/' + encodedAopId)` |
| `templates/explore.html Map button` | `/?ke_id=` | `href` navigation | WIRED | Line 473: `href="/?ke_id=${encodedKe}"` |
| `templates/stats.html export buttons` | `/api/v1/mappings` with `format=csv` | dynamic href update | WIRED | Lines 168-171: `$('#export-json-btn').attr('href', ...)` and `$('#export-csv-btn').attr('href', ...)` |
| `src/blueprints/main.py stats()` | `get_mapping_stats()` | direct call | WIRED | Line 509: `mapping_stats = get_mapping_stats() if mapping_model else {...}` |
| `src/blueprints/v1_api.py _respond_collection` | `request.args.get('format')` | format param check | WIRED | Lines 149-151 check `format_param == "csv"` before Accept header check |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| KE-01 | 04-01, 04-02, 04-05 | KE context panel visible during mapping workflow — shows KE description, AOP context, and biological level | SATISFIED | `/api/ke_detail` endpoint (04-01) + unified collapsible panel with all 5 fields in `main.js` (04-02) |
| EXPLO-01 | 04-03, 04-05 | Explore page filterable by AOP — shows all approved KE mappings belonging to a selected AOP | SATISFIED | AOP Select2 filter in `explore.html`; passes `aop_id` to `/api/v1/mappings` AJAX DataTable |
| EXPLO-02 | 04-03, 04-05 | Explore page filterable by confidence level (High/Medium/Low) | SATISFIED | Confidence toggle buttons in `explore.html`; passes `confidence_level` to DataTable AJAX params |
| EXPLO-03 | 04-03, 04-05 | Coverage gap view — shows which KEs in a selected AOP have no approved mappings yet | SATISFIED | Coverage Gaps third tab in `explore.html`; `loadCoverageGaps()` cross-references `/get_aop_kes/` vs `/api/v1/mappings`; Map button with `/?ke_id=` link |
| EXPLO-05 | 04-04, 04-05 | Dataset metrics dashboard showing mapping counts and coverage statistics | SATISFIED | `/stats` route (no login); `stats.html` with metric cards, confidence breakdown table, AOP coverage indicator |
| EXPLO-06 | 04-04, 04-05 | Custom download interface — user filters dataset then exports the matching subset | SATISFIED | Export buttons with dynamic hrefs in `stats.html`; `?format=csv` support in `v1_api.py` |
| EXPLO-04 | Phase 2 (not Phase 4) | All API responses include stable permanent mapping IDs | NOT IN SCOPE | Assigned to Phase 2 — correctly excluded from Phase 4 plans |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `static/js/main.js` | 260, 312, 360 | `placeholder:` strings | Info | These are Select2 UI placeholder texts, not stub implementations |
| `templates/explore.html` | 211-217 | `placeholder=` attributes | Info | HTML form input placeholders — not stub implementations |

No blocker anti-patterns found. No `TODO/FIXME/XXX`, empty returns, or stub implementations detected in any Phase 4 modified files.

### Coverage Threshold Note

`make test` exits with error code due to `--cov-fail-under=80` in `pytest.ini` (configured since initial project setup, well before Phase 4). All 66 tests pass. Total coverage is 40.51% — this is a structural pre-existing gap (modules like `src/exporters/`, `src/suggestions/pathway.py`, `src/services/embedding.py` have 0-11% coverage). Phase 4 did not introduce this failure and did not add new untested paths beyond what already existed. This is flagged as a warning, not a Phase 4 blocker.

### Human Verification Required

**1. KE Context Panel — Visual Render and Collapse Behavior (KE-01)**

**Test:** Start server (`python app.py`), visit `http://localhost:5000`, select any KE from the KE dropdown (e.g., type "KE 55"). Observe panel. Click the panel summary to collapse. Click again to expand. Open browser Network tab to confirm `/api/ke_detail/` was called and `/api/ke_context/` was NOT called.

**Expected:** Single collapsible `<details>` panel with KE title in bold in summary line, biolevel badge inline, description below summary, AOP membership table (or "No AOP membership" message), and "View on AOP-Wiki" link. Panel starts open, collapses on click.

**Why human:** Panel insertion is done via jQuery `after()` — visual layout, click behavior, and network call identity can only be confirmed in a live browser.

---

**2. URL Param Pre-fill (KE-01 + EXPLO-03 integration)**

**Test:** Visit `http://localhost:5000/?ke_id=KE%2055` directly.

**Expected:** KE 55 appears pre-selected in the KE dropdown without manual interaction, and the context panel auto-loads immediately.

**Why human:** The pre-fill uses a `setTimeout(..., 100)` to wait for Select2 — cannot verify timing behavior statically.

---

**3. Explore Page — Live AOP and Confidence Filters with Chips (EXPLO-01, EXPLO-02)**

**Test:** Visit `http://localhost:5000/explore`. On the KE-WP Mappings tab: (a) select an AOP from the Select2 dropdown, observe filter chip and table reload; (b) click "High" confidence, observe second chip; (c) click "x" on AOP chip, observe chip removal and table reload; (d) click "Clear all".

**Expected:** Table rows are loaded via AJAX (empty `<tbody>` in HTML source). Each filter action triggers a DataTable reload. Both chips display simultaneously when both filters are active. Clear all removes both chips and shows all mappings.

**Why human:** AJAX DataTable behavior and DOM chip rendering require live browser execution.

---

**4. Coverage Gaps Tab (EXPLO-03)**

**Test:** On `/explore`, click "Coverage Gaps" tab. Select an AOP from the dropdown. Observe the gaps table. Click the "Map" button on any row.

**Expected:** Gaps table loads with KE ID, KE Title, Biological Level, and Map button for each KE with no approved mapping. Clicking Map navigates to `/?ke_id=KE%20NNN` and pre-selects that KE.

**Why human:** Gap computation compares two live API responses — result count depends on actual DB state. Map button deep-link integration with KE panel requires browser navigation.

---

**5. Stats Page and Filtered Export (EXPLO-05, EXPLO-06)**

**Test:** Open an incognito/private browser window. Visit `http://localhost:5000/stats`. (a) Observe metric cards and confidence table. (b) Select an AOP from the AOP dropdown. (c) Observe coverage indicator appearance. (d) Click "Download CSV".

**Expected:** Page loads without login redirect (200). Three metric cards show real numeric values. Confidence table shows High/Medium/Low rows. After AOP selection, coverage indicator reads "Coverage: X of Y KEs in AOP N have approved KE-WP mappings." Download CSV triggers a file download with column headers and data rows.

**Why human:** No-login check requires unauthenticated browser request. Metric card values depend on DB state. CSV download behavior is browser-specific.

### Gaps Summary

No gaps found. All 12 must-have truths are verified in the codebase. All key links are wired. All six requirement IDs (KE-01, EXPLO-01, EXPLO-02, EXPLO-03, EXPLO-05, EXPLO-06) have implementation evidence. The 5 human verification items are required because they involve visual rendering, DOM manipulation, browser AJAX timing, and live database state — none of which can be confirmed by static code analysis.

The `make test` coverage threshold failure (40.51% vs 80% target) is pre-existing from before Phase 4 and is not caused by Phase 4 changes.

---

_Verified: 2026-02-21T17:34:45Z_
_Verifier: Claude (gsd-verifier)_
