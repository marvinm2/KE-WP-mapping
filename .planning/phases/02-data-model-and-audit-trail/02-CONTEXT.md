# Phase 2: Data Model and Audit Trail - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add provenance, stable identifiers, and data quality fields to the mapping database before the API freezes the schema. This phase covers: confidence level capture during the proposal workflow, duplicate detection blocking re-submission of already-mapped pairs, stable UUIDs assigned at proposal time, and surfacing curator attribution in the browse table and detail view. Schema changes, validation logic, and UI feedback are all in scope. The public API and export formats are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Confidence level capture
- Set by the curator at proposal submit time (not by admin at approval)
- Three options: High / Medium / Low
- Required field — proposal cannot be submitted without selecting a confidence level
- Presented as select buttons, added to the existing 4-question form interface alongside the current proposal questions

### Duplicate detection UX
- Both approved mappings AND pending proposals block re-submission — strictest policy
- Applies to both KE-WP and KE-GO mapping types equally
- Live check — triggered as soon as the KE and pathway/GO term are selected (before curator completes the form)
- When blocked, show an inline preview of the existing mapping/proposal (not just a text error)
- If a pending proposal is blocking, the curator can flag it as stale for admin review directly from the inline preview
- If an approved mapping exists, the curator can submit a revision proposal (flags the existing mapping for update, goes back to admin review)

### UUID assignment and lifecycle
- UUID assigned at proposal time — every proposal gets a stable UUID immediately on creation
- UUIDs are visible in the admin UI and in all API output; not shown to regular curators in the standard browse/proposal views
- UUIDs are always reserved — never reused even if a proposal is rejected or deleted (old UUIDs return 404/410)

### Provenance display
- Curator GitHub username and approval timestamp shown in both the browse table and the detail view
- Browse table display style: Claude's discretion (inline columns vs tooltip — pick what fits the existing layout)
- BioBERT suggestion score stored with each proposal but only visible in the admin view and API output (not in the curator browse table)
- GitHub username auto-captured from the GitHub OAuth session at proposal submission time — curator does not enter it manually

### Claude's Discretion
- URL routing strategy for individual mapping records (UUID-based `/mappings/{uuid}` vs integer IDs in URLs)
- Browse table column layout for provenance (inline Curator/Date columns vs hover tooltip)
- Exact inline preview component design for duplicate detection warning

</decisions>

<specifics>
## Specific Ideas

- The proposal form already has a 4-question interface with select buttons — confidence level is a natural addition to that existing pattern
- The duplicate detection inline preview should allow action (flag stale / submit revision) directly, not just display
- Suggestion scores are audit/research data, not curator-facing quality signals — keep them out of the main UI

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-data-model-and-audit-trail*
*Context gathered: 2026-02-20*
