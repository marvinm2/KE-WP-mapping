# Phase 4: Curator UX and Explore - Research

**Researched:** 2026-02-21
**Domain:** Flask/Jinja2 UX enhancements, SQLite aggregate queries, DataTables server-side filtering, public stats page
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### KE context panel (KE-01)
- Show in the mapping workflow when a curator selects a KE
- Content: KE title prominently at top, KE description, AOP context (which AOP(s) it belongs to), biological level, and a clickable link to the AOP-Wiki page for that KE
- Auto-loads when a KE is selected — no manual trigger required
- Collapsible: curator can collapse the panel to save screen space
- Data source: KE data (description, AOP membership, biological level) pre-fetched from AOP-Wiki and stored in the local database — fast and offline-capable; do NOT use live SPARQL per request
- Also pre-fetch/store the AOP-Wiki URL per KE so the link can be rendered without an external call

#### Explore filter UX (EXPLO-01, EXPLO-02)
- AOP filter: single-select dropdown with search-as-you-type (type AOP name or ID to filter the list)
- Confidence filter: Claude's discretion — choose the control that fits the existing explore page style
- Filters are combinable with AND logic
- Live filtering: table re-queries immediately when any filter changes — no Apply button
- Active filters shown as removable chips/tags above the table (e.g., "AOP: 123 ×" and "Confidence: High ×")

#### Coverage gap view (EXPLO-03)
- Lives as a tab on the explore page — two tabs: "Mapped" and "Gaps"
- AOP scoping: Claude's discretion — decide whether to require AOP selection or show a global list by default
- Each gap row shows: KE ID, KE title, biological level
- Direct action button on each row: "Map" pre-fills the mapping workflow with that KE's ID selected

#### Metrics dashboard (EXPLO-05, EXPLO-06)
- Separate public page (e.g., /stats) — no login required; visible to anyone
- Metrics: total approved mappings (KE-WP and KE-GO individually and combined), coverage by AOP (X of Y KEs have approved mappings), breakdown by confidence level
- Filter + export: filter by AOP and/or confidence, download matching subset
- Export format: same content-negotiation pattern as /api/v1/ — JSON or CSV depending on Accept header / download button choice

### Claude's Discretion
- KE context panel layout/position (side panel, inline accordion, etc.) — fit the existing single-template layout
- Confidence filter control type on explore page — choose what fits the existing table UI
- Whether coverage gap view requires AOP selection or shows global by default
- Exact metrics page layout (stat cards, tables, charts — whatever communicates coverage clearly)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPLO-01 | Explore page filterable by AOP — shows all approved KE mappings belonging to a selected AOP | `/api/v1/mappings?aop_id=` already resolves AOP → KE IDs via SPARQL+cache. The explore page must be refactored to call this endpoint live instead of rendering server-side. |
| EXPLO-02 | Explore page filterable by confidence level (High/Medium/Low) | `/api/v1/mappings?confidence_level=` already supported. Confidence filter with toggle buttons matches existing `.method-filter-btn` pattern. |
| EXPLO-03 | Coverage gap view — shows which KEs in a selected AOP have no approved mappings yet | Requires: fetch KEs for AOP (via `/get_aop_kes/<aop_id>`), fetch mapped KE IDs, compute difference. The "Map" button needs to set `ke_id` on index page — use URL param `/?ke_id=KE%2055`. |
| EXPLO-05 | Dataset metrics dashboard showing mapping counts and coverage statistics | New `/stats` route in `main_bp`. Queries both `mappings` and `ke_go_mappings` tables for counts. Coverage by AOP requires joining AOP→KE data (SPARQL+cache or pre-computed JSON). |
| EXPLO-06 | Custom download interface — user filters dataset then exports the matching subset | Re-use `_respond_collection` + `_flatten_for_csv` pattern from `v1_api.py`. The stats page filter state drives an export URL that hits `/api/v1/mappings` or a new `/api/v1/stats/export` endpoint. |
| KE-01 | KE context panel visible during mapping workflow — shows KE description, AOP context, and biological level | Most data (description, biolevel, KEpage URL) already in `ke_metadata.json` and loaded into `#ke-preview`. AOP membership is NOT in `ke_metadata.json` — requires a new pre-fetch script writing `data/ke_aop_membership.json`. The existing `.ke-context-panel` CSS and `displayKEContext()` JS need enhancement to match the KE-01 spec. |
</phase_requirements>

---

## Summary

Phase 4 is a UX-heavy phase that surfaces data already present in the database and metadata files. The backend API infrastructure (v1_api.py with AOP+confidence filters, content-negotiated export) is complete from Phase 3. The primary work is frontend enhancements and a few new server-side routes.

**KE-01** is the most nuanced requirement. A KE preview panel (`#ke-preview`) and a context panel (`.ke-context-panel`) already exist in `main.js` and `main.css`. However, they are separate HTML elements and the current context panel only shows AOP membership counts + existing mappings fetched live via SPARQL. The decision locks in local pre-fetching — a new `data/ke_aop_membership.json` file is needed (one AOP membership list per KE ID), populated by a new script similar to `scripts/precompute_ke_embeddings.py`. The panel itself needs collapsible behavior and KE title at the top (currently the title is in `#ke-preview`, not the context panel). The implementation decision is to enhance the existing `showKEPreview()` + `displayKEContext()` to produce a single unified collapsible panel meeting KE-01 spec.

**EXPLO-01/02** require converting the explore page's DataTable from server-side-rendered rows to an AJAX-driven fetch against `/api/v1/mappings`. The `/api/v1/mappings` endpoint already accepts `aop_id` (resolved via SPARQL+cache) and `confidence_level` filters combinably. Active filter chips need a thin JS layer on top of the existing DataTable config.

**EXPLO-03** requires AOP selection (recommend requiring it rather than global default — the full 1561-KE gap list is too large to be useful and the SPARQL resolution would always be needed anyway). The "Map" button can pass `?ke_id=KE%2055` to `/` and the existing `loadKEOptions` / `Select2` logic on `index.html` can pre-select it.

**EXPLO-05/06** need a new `/stats` route, template, and two SQL aggregate queries. The export should reuse the content-negotiation helper from `v1_api.py`. No new DB tables needed.

**Primary recommendation:** Implement in task order: (1) pre-fetch AOP membership script, (2) KE-01 context panel enhancement, (3) explore AJAX refactor with filter chips, (4) coverage gap tab, (5) /stats page with export.

---

## Standard Stack

### Core (already in use — no additions needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| jQuery | 3.6.0 | DOM, AJAX, event handling | Already used for all frontend interactions |
| DataTables | 1.11.5 | Interactive, paginated tables | Already used for explore + admin pages |
| Select2 | 4.1.0-rc.0 | Searchable dropdown | Already used for AOP filter and KE select on index page |
| Flask/Jinja2 | Current project version | Server-side routing + templates | App factory pattern already in use |
| SQLite3 | Python stdlib | Database queries | Auto-migration pattern established |

### Supporting (already in use — reuse patterns)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| DataTables Buttons | 2.2.3 | CSV/Excel/PDF export from table | Keep for existing mapped table export |
| requests | Current | SPARQL via HTTP | AOP resolution (SPARQL+cache pattern already established) |

### No New Dependencies Needed

This phase adds no new libraries. All required capabilities exist in the current stack:
- Filter chips: plain JS/CSS — no library needed
- Stats page charts (discretionary): use plain CSS stat cards, not a chart library (simpler, already fits design system)
- Content-negotiated export: `_respond_collection` pattern from `v1_api.py` — copy-adapt it

---

## Architecture Patterns

### Pattern 1: Pre-compute AOP Membership (new script)

**What:** Fetch all AOP→KE relationships from AOP-Wiki SPARQL once, write `data/ke_aop_membership.json` — a dict keyed by KE label with list of `{aop_id, aop_title}`.

**When to use:** At data refresh time (alongside re-running `precompute_ke_embeddings.py`). The app reads this at startup via `ServiceContainer` (same pattern as `ke_metadata.json`).

**Structure of `data/ke_aop_membership.json`:**
```json
{
  "KE 55": [
    {"aop_id": "AOP 1", "aop_title": "Inhibition of the mitochondrial..."}
  ],
  "KE 100": [],
  "KE 123": [...]
}
```

**New script:** `scripts/precompute_ke_aop_membership.py` — queries AOP-Wiki for all AOP→KE pairs in one SPARQL call (not per-KE), writes the JSON. One SPARQL query, not 1561.

**Efficient SPARQL query pattern:**
```sparql
PREFIX aopo: <http://aopkb.org/aop_ontology#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-manager#>

SELECT DISTINCT ?aopId ?aopTitle ?keId
WHERE {
    ?aop a aopo:AdverseOutcomePathway ;
         rdfs:label ?aopId ;
         dc:title ?aopTitle ;
         aopo:has_key_event ?ke .
    ?ke rdfs:label ?keId .
}
ORDER BY ?aopId ?keId
```

### Pattern 2: KE-01 Context Panel (enhance existing JS + HTML)

**What:** Unify `showKEPreview()` and `displayKEContext()` into a single collapsible panel that meets KE-01 spec.

**Current state:**
- `#ke-preview`: shows title, description, biolevel badge, AOP-Wiki link (data from `ke_metadata.json` via `data-*` attributes on `<option>`)
- `.ke-context-panel`: shows AOP membership, WP/GO mapping counts (data from `/api/ke_context/` SPARQL)

**Target state (KE-01):**
- Single `#ke-context-panel` div, collapsible via `<details>`/`<summary>` (already used in this panel)
- Summary line: KE title prominently + biolevel badge
- Body: description (truncated with expand), AOP membership list (from `ke_aop_membership.json` via new `/api/ke_aop_membership/<ke_id>` endpoint or loaded into option `data-aops` attribute), AOP-Wiki link
- Data source: all from `ke_metadata.json` (title, description, biolevel, KEpage) + `ke_aop_membership.json` (AOP membership) — NO live SPARQL per request

**Implementation choice:** Load AOP membership into the `<option>` elements (as a JSON-encoded `data-aops` attribute) when `get_ke_options` is called. Since `ke_aop_membership.json` is loaded at startup by `ServiceContainer`, the `/get_ke_options` endpoint can embed AOP membership in each option without an extra AJAX call.

**Alternative:** Add a new endpoint `/api/ke_detail/<ke_id>` that returns combined data from both JSON files. Simpler for incremental implementation and avoids bloating the `<option>` data attributes for 1561 KEs.

**Recommendation:** Endpoint approach — `/api/ke_detail/<ke_id>` reading from both JSON files at request time (fast, no SPARQL). Called from JS in `handleKESelection()`, replaces the current `loadKEContext()` which hits SPARQL.

**CSS:** The existing `.ke-context-panel` and `.context-badge` classes already exist. Add `.ke-context-title` for the prominent title display.

### Pattern 3: Explore Page AJAX Refactor (EXPLO-01/02)

**What:** Convert explore page from server-rendered rows to DataTables AJAX mode hitting `/api/v1/mappings`.

**Current state:** Explore page receives `dataset` (all mappings, list of dicts) via Jinja2 context and renders `{% for row in dataset %}` rows. DataTables operates in client-side mode.

**Target state:** DataTables in AJAX server-side mode, fetching from `/api/v1/mappings?page=N&per_page=50&aop_id=X&confidence_level=Y`.

**DataTables AJAX config pattern:**
```javascript
$('#datasetTable').DataTable({
    serverSide: true,
    ajax: function(data, callback, settings) {
        const params = new URLSearchParams({
            page: Math.floor(data.start / data.length) + 1,
            per_page: data.length,
        });
        if (activeAopId) params.set('aop_id', activeAopId);
        if (activeConfidence) params.set('confidence_level', activeConfidence);

        fetch(`/api/v1/mappings?${params}`)
            .then(r => r.json())
            .then(json => {
                callback({
                    draw: data.draw,
                    recordsTotal: json.pagination.total,
                    recordsFiltered: json.pagination.total,
                    data: json.data
                });
            });
    },
    columns: [/* uuid, ke_id, ke_name, pathway_id, pathway_title, confidence_level, approved_by, approved_at */]
});
```

**Filter chip pattern (plain JS):**
```javascript
// State
let activeAopId = null, activeAopLabel = null;
let activeConfidence = null;

function applyFilters() {
    // Re-draw DataTable — ajax function reads activeAopId and activeConfidence
    table.ajax.reload();
    renderFilterChips();
}

function renderFilterChips() {
    const chips = [];
    if (activeAopId) chips.push(`<span class="filter-chip">AOP: ${activeAopLabel} <button onclick="clearAop()">×</button></span>`);
    if (activeConfidence) chips.push(`<span class="filter-chip">Confidence: ${activeConfidence} <button onclick="clearConfidence()">×</button></span>`);
    $('#active-filters').html(chips.join(''));
}
```

**Confidence filter control choice (Claude's discretion):** Use the existing `.method-filter-btn` toggle-button pattern (already used for suggestion method filter). Three buttons: "High", "Medium", "Low", plus "All" (default). This matches the existing style, requires no new UI components, and visually groups well above the DataTable.

**AOP filter control choice:** Use Select2 (same as the AOP filter on `index.html`) — search-as-you-type is required by the locked decision. The AOP options can be fetched from `/get_aop_options` (SPARQL+cache, same call as index.html).

### Pattern 4: Coverage Gap View (EXPLO-03)

**What:** A "Gaps" tab on the explore page showing unmapped KEs for a selected AOP.

**AOP scoping recommendation (Claude's discretion):** Require AOP selection rather than a global default. Rationale: with 1561 KEs and only 24 mapped KEs currently, a global gaps view would show 1537 rows (not useful). AOP scoping makes the list actionable (10–40 KEs per AOP typically). Show a placeholder when no AOP is selected.

**Data flow:**
1. Curator selects an AOP in the gaps-tab AOP dropdown
2. JS calls `/get_aop_kes/<aop_id>` → list of KE IDs in that AOP
3. JS calls `/api/v1/mappings?aop_id=<id>&per_page=200` → list of mapped KE IDs in that AOP
4. JS computes difference: unmapped = aop_kes - mapped_ke_ids
5. Render gap table: KE ID | KE title | Biological level | Map button

**"Map" button pre-fill:** Navigate to `/?ke_id=KE%2055`. Add a handler in `main.js` `init()` that checks `URLSearchParams` for `ke_id` on page load:
```javascript
const params = new URLSearchParams(window.location.search);
const preselectedKE = params.get('ke_id');
if (preselectedKE) {
    $('#ke_id').val(preselectedKE).trigger('change');
}
```
This uses the existing Select2 initialization and `handleKESelection()` flow.

**Tab structure on explore page:**
```
[KE-WP Mappings] [KE-GO Mappings] [Coverage Gaps]
```
The gaps tab is a third tab added to the existing two-tab switcher.

### Pattern 5: /stats Page (EXPLO-05/06)

**What:** New public page at `/stats` with aggregate metrics and filtered export.

**Route:** Add to `main_bp` in `src/blueprints/main.py`. No `@login_required`. Pass pre-computed stats as template context.

**Stats queries:**
```sql
-- Total mappings
SELECT COUNT(*) FROM mappings;
SELECT COUNT(*) FROM ke_go_mappings;

-- By confidence level (KE-WP)
SELECT confidence_level, COUNT(*) as count
FROM mappings
GROUP BY LOWER(confidence_level);

-- By confidence level (KE-GO)
SELECT confidence_level, COUNT(*) as count
FROM ke_go_mappings
GROUP BY LOWER(confidence_level);
```

**Coverage by AOP:** Cannot be computed purely from SQL because AOP→KE membership is in `ke_aop_membership.json` (or SPARQL cache), not the DB. Options:
1. Load `ke_aop_membership.json` at startup (done by `ServiceContainer`) and compute coverage in Python at request time: for each AOP, count total KEs, query `SELECT DISTINCT ke_id FROM mappings WHERE ke_id IN (...)`, compute ratio.
2. Show AOP coverage only when user selects an AOP filter on `/stats`.

**Recommendation:** Option 2 (lazy AOP coverage) — show global totals immediately, AOP coverage when AOP is selected via a filter dropdown. This avoids a slow startup computation over all AOPs.

**Layout (Claude's discretion):** Stat cards + one table. Structure:
```
[ Total KE-WP: N ] [ Total KE-GO: M ] [ Total: N+M ]

Confidence breakdown table:
Level | KE-WP | KE-GO | Total
High  |   X   |   Y   |  X+Y
Medium|   X   |   Y   |  X+Y
Low   |   X   |   Y   |  X+Y

[Optional: AOP filter dropdown → shows coverage for selected AOP]

[Export filtered dataset as JSON] [Export filtered dataset as CSV]
```

**Export:** The export buttons call `/api/v1/mappings?<filters>` with `Accept: text/csv` or `Accept: application/json` — the existing content-negotiation in `_respond_collection` handles it. No new API endpoint needed for the basic case.

For a "download button" flow that doesn't require setting Accept headers in browser: add `?format=csv` query param support to `/api/v1/mappings` as a fallback (checks `request.args.get('format')` before `Accept` header). This is a small addition to `_respond_collection`.

### Anti-Patterns to Avoid

- **Live SPARQL per KE selection for context panel:** The decision explicitly forbids this. Use `ke_aop_membership.json`.
- **Server-side DataTable re-render for filter changes:** The current explore page re-renders all rows server-side. Do NOT add `?aop_id=` to the `/explore` Flask route and re-render Jinja2 rows — instead, convert to AJAX DataTable using `/api/v1/mappings`.
- **Inline styles in new HTML:** The codebase has done CSS consolidation. Use existing CSS tokens and classes. New styles go in `main.css` as classes.
- **Full global gap list without AOP scope:** 1537 unmapped KEs is unusable. Always scope to a selected AOP.
- **Embedding all 1561 AOP memberships as `data-*` on `<option>` elements:** This would bloat the page significantly (potentially 100s of KB of HTML). Use the endpoint approach for AOP membership.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Search-as-you-type AOP dropdown | Custom autocomplete | Select2 (already loaded) | Already used on index.html, same CDN, same config pattern |
| Content-negotiated JSON/CSV export | Custom format detection | `_respond_collection` from `v1_api.py` | Already tested, handles `Accept` header and CSV flattening |
| KE-in-AOP resolution | Per-request SPARQL | `ke_aop_membership.json` + in-memory lookup | Decision locks this; SPARQL has latency and offline risk |
| AOP→KE resolution for explore filter | Per-request SPARQL | Existing `_resolve_aop_ke_ids()` in `v1_api.py` + `sparql_cache` | Already implemented and cached; reuse from `/api/v1/mappings?aop_id=` |
| Stats aggregation | Hand-written Python loops | SQL `GROUP BY` + `COUNT(*)` | SQL is correct, fast, and already how the models work |

---

## Common Pitfalls

### Pitfall 1: AOP Membership Not in ke_metadata.json

**What goes wrong:** Developer assumes `ke_metadata.json` has AOP membership fields. It does not. Fields are: `KElabel`, `KEtitle`, `KEdescription`, `biolevel`, `KEpage`.

**Why it happens:** The KE context panel uses SPARQL for AOP membership today; AOP membership was never added to the pre-computed JSON.

**How to avoid:** Write `scripts/precompute_ke_aop_membership.py` as the first task. The new `/api/ke_detail/<ke_id>` endpoint reads from both `ke_metadata.json` and `ke_aop_membership.json` — neither alone is sufficient.

**Warning signs:** `/api/ke_context/` currently hits SPARQL live for AOP membership. The KE-01 spec says "do NOT use live SPARQL per request" — the current endpoint violates this when the cache misses.

### Pitfall 2: DataTables Server-Side Mode vs Client-Side Mode

**What goes wrong:** The existing explore page uses DataTables in client-side mode (all data in DOM). Adding `serverSide: true` while also keeping Jinja2-rendered rows causes double-initialization or rendering conflicts.

**Why it happens:** DataTables with `serverSide: true` ignores `<tbody>` HTML rows and fetches entirely from the `ajax` function. If the template still renders rows, there will be a flash of server-rendered content before DataTables replaces it.

**How to avoid:** When converting to AJAX mode, remove the `{% for row in dataset %}` loop from the template and pass an empty `<tbody>`. The Flask route can still pass `dataset=[]` or remove it entirely.

**Warning signs:** DataTables showing double rows or "Showing 0 to 0 of 0 entries" initially.

### Pitfall 3: URL-Based KE Pre-fill on Index Page

**What goes wrong:** The `select2` for `#ke_id` is initialized asynchronously (after fetching `/get_ke_options`). Setting `$('#ke_id').val(...)` before Select2 is initialized has no effect.

**Why it happens:** `loadKEOptions()` is async; the URL param is read synchronously at page load. The dropdown is not yet populated.

**How to avoid:** Store the `preselectedKE` value on `this` during `init()`. In `populateKEDropdown()` (the callback that actually sets up the `<option>` elements), check for `this.preselectedKE` after Select2 init and trigger change:
```javascript
if (this.preselectedKE) {
    $('#ke_id').val(this.preselectedKE).trigger('change');
    this.preselectedKE = null;
}
```

**Warning signs:** KE dropdown shows correct value selected but `handleKESelection()` never fires, so preview and suggestions don't load.

### Pitfall 4: Stats Page AOP Coverage With Many AOPs

**What goes wrong:** Computing "coverage for every AOP" at `/stats` page load requires either: (a) one SQL query per AOP (hundreds of queries), or (b) loading `ke_aop_membership.json` and running Python set operations, which may be slow for 300+ AOPs.

**Why it happens:** AOP→KE membership is not in the database; it's in a JSON file.

**How to avoid:** Compute AOP coverage only on-demand (when curator selects an AOP on `/stats`), not for all AOPs simultaneously. The `<aop_id>` param on the stats page filter triggers a lightweight query:
```sql
SELECT ke_id FROM mappings WHERE ke_id IN (?, ?, ...)
```
where the `?` list comes from `ke_aop_membership.json[aop_id]`.

### Pitfall 5: GO Mappings Missing From AOP Coverage

**What goes wrong:** The "coverage" metric for EXPLO-05 says "KEs with approved mappings" — a KE with only a GO mapping and no WP mapping might be counted as "unmapped" if only `mappings` table is queried.

**Why it happens:** Coverage by AOP for KE-01 is ambiguous: does "mapping" mean KE-WP mapping, any mapping, or either?

**How to avoid:** The spec says "coverage by AOP: for each AOP, X of Y KEs have approved mappings." Based on context (this is the KE-WP mapping tool), "approved mappings" in the coverage metric means KE-WP mappings. KE-GO coverage is a separate concept. Confirm this interpretation in the plan — if wrong, fix the SQL to UNION both tables.

---

## Code Examples

### New Endpoint: /api/ke_detail/<ke_id>

```python
# In src/blueprints/api.py or a new utility blueprint

@api_bp.route("/api/ke_detail/<ke_id>", methods=["GET"])
@general_rate_limit
def get_ke_detail(ke_id):
    """
    Get KE detail from pre-fetched local data.
    Returns: title, description, biolevel, ke_page, aop_membership
    No live SPARQL — reads ke_metadata.json + ke_aop_membership.json.
    """
    if not ke_metadata:
        return jsonify({"error": "KE metadata not available"}), 503

    # Find KE in metadata (dict lookup via list scan; consider pre-indexing)
    ke_data = next(
        (ke for ke in ke_metadata if ke.get("KElabel") == ke_id),
        None
    )
    if not ke_data:
        return jsonify({"error": f"KE not found: {ke_id}"}), 404

    aop_membership = ke_aop_membership.get(ke_id, []) if ke_aop_membership else []

    return jsonify({
        "ke_id": ke_id,
        "ke_title": ke_data.get("KEtitle", ""),
        "ke_description": ke_data.get("KEdescription", ""),
        "biolevel": ke_data.get("biolevel", ""),
        "ke_page": ke_data.get("KEpage", ""),
        "aop_membership": aop_membership,
    })
```

Note: `ke_metadata` is a list. For 1561 entries, linear scan per request is fast enough (< 1ms), but pre-indexing as a dict keyed by `KElabel` is better. Add to `ServiceContainer`.

### Pre-fetch Script Pattern (new)

```python
# scripts/precompute_ke_aop_membership.py
# Pattern mirrors precompute_ke_embeddings.py

SPARQL_QUERY = """
PREFIX aopo: <http://aopkb.org/aop_ontology#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?aopId ?aopTitle ?keId
WHERE {
    ?aop a aopo:AdverseOutcomePathway ;
         rdfs:label ?aopId ;
         dc:title ?aopTitle ;
         aopo:has_key_event ?ke .
    ?ke rdfs:label ?keId .
}
ORDER BY ?aopId ?keId
"""

# Fetch once, group by keId, write data/ke_aop_membership.json
# Output: {"KE 55": [{"aop_id": "AOP 1", "aop_title": "..."}], ...}
```

### Stats SQL Aggregates

```python
def get_mapping_stats(conn):
    """
    Returns aggregated stats for the /stats page.
    Reads from both mappings and ke_go_mappings tables.
    """
    wp_total = conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
    go_total = conn.execute("SELECT COUNT(*) FROM ke_go_mappings").fetchone()[0]

    wp_by_confidence = {
        row[0].lower(): row[1]
        for row in conn.execute(
            "SELECT LOWER(confidence_level), COUNT(*) FROM mappings GROUP BY LOWER(confidence_level)"
        ).fetchall()
    }
    go_by_confidence = {
        row[0].lower(): row[1]
        for row in conn.execute(
            "SELECT LOWER(confidence_level), COUNT(*) FROM ke_go_mappings GROUP BY LOWER(confidence_level)"
        ).fetchall()
    }

    return {
        "wp_total": wp_total,
        "go_total": go_total,
        "total": wp_total + go_total,
        "wp_by_confidence": wp_by_confidence,
        "go_by_confidence": go_by_confidence,
    }
```

### Active Filter Chip CSS (new classes)

```css
/* Add to static/css/main.css */
.filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 32px;
    margin-bottom: 12px;
    align-items: center;
}

.filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px 4px 12px;
    background: var(--color-secondary-light-blue);
    border: 1px solid var(--color-primary-blue);
    border-radius: var(--radius-full);
    font-size: var(--font-size-sm);
    color: var(--color-primary-dark);
}

.filter-chip-remove {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-primary-blue);
    font-size: 16px;
    line-height: 1;
    padding: 0;
}
```

### explore.html AJAX DataTable Initialization

```javascript
// Replace the existing DataTable init that uses Jinja rows
const wpTable = $('#datasetTable').DataTable({
    serverSide: true,
    processing: true,
    ajax: function(data, callback, settings) {
        const params = new URLSearchParams({
            page: Math.floor(data.start / data.length) + 1,
            per_page: data.length,
        });
        if (state.aopId) params.set('aop_id', state.aopId);
        if (state.confidence) params.set('confidence_level', state.confidence);

        fetch(`/api/v1/mappings?${params}`, {
            headers: { 'Accept': 'application/json' }
        })
        .then(r => r.json())
        .then(json => {
            callback({
                draw: data.draw,
                recordsTotal: json.pagination.total,
                recordsFiltered: json.pagination.total,
                data: json.data
            });
        })
        .catch(() => callback({ draw: data.draw, recordsTotal: 0, recordsFiltered: 0, data: [] }));
    },
    columns: [
        { data: 'ke_id', title: 'KE ID' },
        { data: 'ke_name', title: 'KE Title' },
        { data: 'pathway_id', title: 'WP ID' },
        { data: 'pathway_title', title: 'WP Title' },
        { data: 'confidence_level', title: 'Confidence' },
        { data: 'provenance.approved_by', title: 'Curator', defaultContent: '—' },
        { data: 'provenance.approved_at', title: 'Approved', defaultContent: '—' },
    ],
    // Keep existing column widths and ordering
    order: [[6, 'desc']],
});
```

### Export Button Pattern (stats page)

```html
<!-- In templates/stats.html -->
<div class="export-controls">
    <a id="export-json-btn" class="btn btn-secondary" href="/api/v1/mappings">
        Download JSON
    </a>
    <a id="export-csv-btn" class="btn btn-secondary" href="/api/v1/mappings?format=csv">
        Download CSV
    </a>
</div>
```

```javascript
// JS updates href when filters change
function updateExportLinks() {
    const params = new URLSearchParams();
    if (state.aopId) params.set('aop_id', state.aopId);
    if (state.confidence) params.set('confidence_level', state.confidence);

    $('#export-json-btn').attr('href', `/api/v1/mappings?${params}`);
    params.set('format', 'csv');
    $('#export-csv-btn').attr('href', `/api/v1/mappings?${params}`);
}
```

Add `?format=csv` support to `_respond_collection` in `v1_api.py`:
```python
def _respond_collection(serialized_rows, pagination, csv_fields):
    format_param = request.args.get('format', '').lower()
    use_csv = format_param == 'csv' or request.accept_mimetypes.best_match(
        ['application/json', 'text/csv'], default='application/json'
    ) == 'text/csv'
    # ... rest of function unchanged
```

---

## State of the Art

| Old Approach | Current Approach | Status | Impact |
|--------------|------------------|--------|--------|
| Live SPARQL for AOP options | SPARQL+24h cache via `sparql_cache` table | In use | AOP dropdown works offline after first load |
| Live SPARQL for KE context | `/api/ke_context/` with SPARQL+cache | In use (but violates KE-01 for first load) | Must replace with pre-fetched JSON |
| Server-rendered explore table | Jinja2 rows, client-side DataTable | In use | Must convert to AJAX for filter support |
| Proposal-only new mappings | All submissions create pending proposals (Phase 3 decision) | Current | No change needed for Phase 4 |

---

## Open Questions

1. **KE metadata indexing — dict vs list**
   - What we know: `ke_metadata.json` is loaded as a list of 1561 dicts. The `ServiceContainer` exposes it as `self._ke_metadata` (list).
   - What's unclear: Whether a dict index by `KElabel` is needed in `ServiceContainer` for fast `/api/ke_detail/<ke_id>` lookups.
   - Recommendation: Add a `ke_metadata_index` property to `ServiceContainer` that builds `{ke["KElabel"]: ke for ke in self._ke_metadata}` on first access. This is a micro-optimization but makes intent clear.

2. **AOP options source for explore page**
   - What we know: The existing `/get_aop_options` endpoint fetches from SPARQL+cache (24h TTL). This is the same endpoint used by `index.html`.
   - What's unclear: Whether the explore page should use the same endpoint or a pre-computed AOP list.
   - Recommendation: Use the same `/get_aop_options` endpoint. It's already cached; adding a second caller is free. Pre-computation of AOP list is out of scope unless the SPARQL endpoint becomes unreliable.

3. **Coverage gap "Map" button and deep-link state restoration**
   - What we know: The `index.html` `#ke_id` Select2 is populated asynchronously. URL param `?ke_id=KE%2055` must be read after the dropdown populates.
   - What's unclear: Whether existing session-based form-state restoration (`restoreFormState()` in `main.js`) conflicts with the URL param approach.
   - Recommendation: URL param takes precedence over session state. Clear `sessionStorage` form state when URL param is present.

4. **GO mappings in gap view**
   - What we know: EXPLO-03 spec says "KEs with no approved mapping." The explore page has both KE-WP and KE-GO tabs.
   - What's unclear: Does a KE with only a GO mapping appear in the gap view (as having no WP mapping)?
   - Recommendation: Gap view should show KEs with no KE-WP mapping (the primary use of this tool). This can be noted in the plan and re-confirmed with the user if needed.

---

## Sources

### Primary (HIGH confidence)

- Codebase direct inspection: `src/blueprints/api.py` — AOP SPARQL endpoints, `/api/ke_context/`, existing AOP+confidence filter patterns on `/api/v1/mappings`
- Codebase direct inspection: `src/blueprints/v1_api.py` — `_respond_collection`, `_flatten_for_csv`, `_resolve_aop_ke_ids`, content-negotiation pattern
- Codebase direct inspection: `static/js/main.js` — `loadKEContext()`, `displayKEContext()`, `showKEPreview()`, `populateKEDropdown()`, Select2 initialization patterns
- Codebase direct inspection: `static/css/main.css` lines 1086–1152 — `.ke-context-panel` styles already exist
- Codebase direct inspection: `data/ke_metadata.json` — fields confirmed as `KElabel`, `KEtitle`, `KEdescription`, `biolevel`, `KEpage`; NO AOP membership fields
- Codebase direct inspection: `templates/explore.html` — current server-render approach; DataTables in client-side mode
- Codebase direct inspection: `src/core/models.py` — `get_mappings_paginated()` accepts `ke_ids` (list) for AOP-scoped queries

### Secondary (MEDIUM confidence)

- DataTables 1.11.5 AJAX/server-side documentation pattern (from training knowledge, consistent with existing usage in codebase): `serverSide: true` + `ajax` function replaces server-rendered rows
- Select2 `allowClear` + empty placeholder option pattern: verified in existing `loadAOPOptions()` implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all confirmed from codebase
- Architecture: HIGH — patterns verified from existing code (v1_api.py, main.js, models.py)
- Pitfalls: HIGH — confirmed from direct inspection (AOP membership gap in ke_metadata.json, async Select2 initialization)
- Open questions: MEDIUM — interpretation questions, not technical unknowns

**Research date:** 2026-02-21
**Valid until:** 2026-04-21 (stable stack; valid until major dependency changes)
