# Phase 4: Curator UX and Explore - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Navigator and discovery layer for curators — adding a KE context panel to the mapping workflow, AOP and confidence filters to the explore page, a coverage gap view, and a public metrics dashboard with filtered export. The underlying data model and API are complete; this phase surfaces what's already there.

Requirements: EXPLO-01, EXPLO-02, EXPLO-03, EXPLO-05, EXPLO-06, KE-01

</domain>

<decisions>
## Implementation Decisions

### KE context panel (KE-01)
- Show in the mapping workflow when a curator selects a KE
- Content: KE title prominently at top, KE description, AOP context (which AOP(s) it belongs to), biological level, and a clickable link to the AOP-Wiki page for that KE
- Auto-loads when a KE is selected — no manual trigger required
- Collapsible: curator can collapse the panel to save screen space
- Data source: KE data (description, AOP membership, biological level) pre-fetched from AOP-Wiki and stored in the local database — fast and offline-capable; do NOT use live SPARQL per request
- Also pre-fetch/store the AOP-Wiki URL per KE so the link can be rendered without an external call

### Explore filter UX (EXPLO-01, EXPLO-02)
- AOP filter: single-select dropdown with search-as-you-type (type AOP name or ID to filter the list)
- Confidence filter: Claude's discretion — choose the control that fits the existing explore page style
- Filters are combinable with AND logic (e.g., "High confidence mappings in AOP 123" works as expected)
- Live filtering: table re-queries immediately when any filter changes — no Apply button
- Active filters shown as removable chips/tags above the table (e.g., "AOP: 123 ×" and "Confidence: High ×")

### Coverage gap view (EXPLO-03)
- Lives as a tab on the explore page — two tabs: "Mapped" and "Gaps"
- AOP scoping: Claude's discretion — decide whether to require AOP selection or show a global list by default
- Each gap row shows: KE ID, KE title, biological level
- Direct action button on each row: "Map" pre-fills the mapping workflow with that KE's ID selected

### Metrics dashboard (EXPLO-05, EXPLO-06)
- Separate public page (e.g., /stats) — no login required; visible to anyone
- Metrics to show:
  - Total approved mappings (KE-WP and KE-GO, individually and combined)
  - Coverage by AOP: for each AOP, X of Y KEs have approved mappings
  - Breakdown by confidence level: count of High / Medium / Low mappings
- Filter + export: user can filter the dataset (at minimum by AOP and/or confidence) then download the matching subset
- Export format: same content-negotiation pattern as /api/v1/ — JSON or CSV depending on Accept header / download button choice

### Claude's Discretion
- KE context panel layout/position (side panel, inline accordion, etc.) — fit the existing single-template layout
- Confidence filter control type on explore page — choose what fits the existing table UI
- Whether coverage gap view requires AOP selection or shows global by default
- Exact metrics page layout (stat cards, tables, charts — whatever communicates coverage clearly)

</decisions>

<specifics>
## Specific Ideas

- KE title should appear prominently at the top of the context panel — not buried in description text
- The AOP-Wiki link should be real and clickable, linking to the specific KE page
- Active filter chips should be removable individually (× on each chip) and ideally there's a "Clear all" option too
- The "Map" button in the gap view should pre-fill the KE field — reduce friction to zero for gap closure
- The metrics page is intentionally public: researchers evaluating the dataset should see how many mappings exist without logging in

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-curator-ux-and-explore*
*Context gathered: 2026-02-21*
