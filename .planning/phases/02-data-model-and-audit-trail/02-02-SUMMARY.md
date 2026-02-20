---
phase: 02-data-model-and-audit-trail
plan: 02
subsystem: api
tags: [sqlite, models, flask, provenance, audit-trail, duplicate-check, proposals]

# Dependency graph
requires:
  - phase: 02-01
    provides: "uuid, approved_by_curator, approved_at_curator columns on mappings/ke_go_mappings; is_stale, uuid columns on proposals/ke_go_proposals"
provides:
  - "check_mapping_exists_with_proposals() — enriched blocking payload with blocking_type, existing, actions"
  - "check_go_mapping_exists_with_proposals() — same structure for KE-GO pairs"
  - "MappingModel.update_mapping() extended with approved_by_curator and approved_at_curator params"
  - "get_all_mappings() and get_mappings_by_ke() return uuid and provenance columns for both model classes"
  - "ProposalModel.flag_proposal_stale() and GoProposalModel.flag_go_proposal_stale()"
  - "UUID4 generation wired into ProposalModel.create_proposal() and GoProposalModel.create_proposal()"
  - "Admin approve_proposal() writes approved_by_curator + approved_at_curator at approval time"
  - "POST /flag_proposal_stale endpoint with @login_required"
  - "/check and /check_go_entry return enriched blocking payloads"
  - "MappingSchema confidence_level required=True (server-side enforcement)"
affects:
  - 02-03  # audit trail display uses approved_by_curator, approved_at_curator, uuid
  - 02-04  # public API blocking check response shape now enriched

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pending_proposal takes priority over approved_mapping in enriched duplicate-check methods — most actionable blocking state shown first"
    - "Enriched check returns {pair_exists, blocking_type, existing, actions} — frontend reads actions to decide which UI path to show"
    - "Provenance written atomically at approval time: admin_username from session, approved_at via datetime.utcnow().isoformat()"

key-files:
  created: []
  modified:
    - src/core/models.py
    - src/blueprints/api.py
    - src/blueprints/admin.py

key-decisions:
  - "pending_proposal takes priority over approved_mapping in check_mapping_exists_with_proposals() — when both exist for a pair, the most actionable state (flag stale, then resubmit) is shown"
  - "flag_proposal_stale endpoint placed in api_bp (not admin_bp) — curators (not only admins) need to flag stale; @login_required is sufficient"
  - "GoMappingModel.update_mapping() not needed for GO approval — admin.py does not yet handle GO proposals; only WP approval flow updated"
  - "schemas.py confidence_level already required=True — no change needed, plan expectation confirmed by test"

patterns-established:
  - "Enriched check method signature: check_X_exists_with_proposals(ke_id, pair_id) -> Dict — returns blocking_type + existing + actions"
  - "Flag-stale method signature: flag_X_proposal_stale(proposal_id, flagged_by) -> bool — single UPDATE, logs, returns True/False"

requirements-completed: [CURAT-01, CURAT-02, CURAT-03]

# Metrics
duration: 6min
completed: 2026-02-20
---

# Phase 2 Plan 02: Data Model and Audit Trail — Enriched Check Endpoints and Provenance Summary

**Enriched duplicate-check endpoints returning blocking_type + existing + actions, curator provenance written at approval time, and /flag_proposal_stale endpoint added to complete the server-side curation audit trail.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-02-20T13:32:00Z
- **Completed:** 2026-02-20T13:38:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `check_mapping_exists_with_proposals()` to `MappingModel` and `check_go_mapping_exists_with_proposals()` to `GoMappingModel` — both return structured `{blocking_type, existing, actions}` payloads for frontend routing; `pending_proposal` blocks with priority over `approved_mapping`
- Extended `MappingModel.update_mapping()` with `approved_by_curator` and `approved_at_curator` params; wired into `admin.py` `approve_proposal()` so every approval writes curator GitHub username and ISO timestamp
- Added `flag_proposal_stale()` to `ProposalModel` and `flag_go_proposal_stale()` to `GoProposalModel` (UPDATE is_stale=1); wired POST `/flag_proposal_stale` endpoint in `api.py` with `@login_required`
- Wired UUID4 generation into `ProposalModel.create_proposal()` and `GoProposalModel.create_proposal()` — every new proposal row now has a non-null UUID4 at insert time
- Extended `get_all_mappings()` and `get_mappings_by_ke()` in both model classes to include `uuid`, `approved_by_curator`, `approved_at_curator` columns

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrich duplicate-check model methods and extend update_mapping() for provenance** - `70ff795` (feat)
2. **Task 2: Wire provenance into admin approval, enrich check endpoints, add /flag_proposal_stale endpoint** - `9214ec5` (feat)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `src/core/models.py` — Added `check_mapping_exists_with_proposals()`, `check_go_mapping_exists_with_proposals()`, `flag_proposal_stale()`, `flag_go_proposal_stale()`; extended `update_mapping()` and all four get-mapping query methods; wired UUID4 into both `create_proposal()` methods
- `src/blueprints/api.py` — Replaced `check_mapping_exists()` calls with enriched versions; added POST `/flag_proposal_stale` endpoint
- `src/blueprints/admin.py` — Added `approved_by_curator` and `approved_at_curator` to `approve_proposal()` mapping update call

## Enriched /check Response Shape (for Plan 03 frontend reference)

**Case 1 — pending proposal exists (highest priority):**
```json
{
  "pair_exists": true,
  "blocking_type": "pending_proposal",
  "existing": {
    "proposal_id": 42,
    "ke_id": "KE 55",
    "wp_id": "WP500",
    "ke_title": "...",
    "wp_title": "...",
    "proposed_confidence": "high",
    "proposed_connection_type": "causative",
    "submitted_by": "githubuser",
    "submitted_at": "2026-02-19T10:00:00"
  },
  "actions": ["flag_stale"]
}
```

**Case 2 — approved mapping exists (no pending proposal):**
```json
{
  "pair_exists": true,
  "blocking_type": "approved_mapping",
  "existing": {
    "ke_id": "KE 55",
    "wp_id": "WP500",
    "ke_title": "...",
    "wp_title": "...",
    "confidence_level": "high",
    "connection_type": "causative",
    "approved_by_curator": "curatoruser",
    "approved_at_curator": "2026-02-15T09:30:00.123456",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "id": 7
  },
  "actions": ["submit_revision"]
}
```

**Case 3 — KE exists with different WP (informational):**
```json
{
  "ke_exists": true,
  "message": "The KE ID KE 55 exists but not with WP ID WP999.",
  "ke_matches": [...]
}
```

**Case 4 — nothing found:**
```json
{
  "ke_exists": false,
  "pair_exists": false,
  "message": "The KE ID KE 55 and WP ID WP999 are new entries."
}
```

Same structure applies to `/check_go_entry` (with `go_id`/`go_name` instead of `wp_id`/`wp_title`).

## /flag_proposal_stale Endpoint Contract

- **Method:** POST
- **URL:** `/flag_proposal_stale`
- **Auth:** `@login_required` (curator or admin)
- **Rate limit:** `@submission_rate_limit`
- **Params:**
  - `proposal_id` (int, required) — database ID of the proposal
  - `mapping_type` (str, optional, default `"wp"`) — `"wp"` or `"go"`
- **Success:** `200 {"message": "Proposal flagged as stale for admin review."}`
- **Errors:** `400` if `proposal_id` missing; `500` if DB update fails; `503` if GO proposal service unavailable

## Admin Approval Provenance Pattern

```python
# In approve_proposal() after update_proposal_status():
approved_at = datetime.utcnow().isoformat()
mapping_model.update_mapping(
    mapping_id=mapping_id,
    connection_type=proposal["proposed_connection_type"],
    confidence_level=proposal["proposed_confidence"],
    updated_by=admin_username,
    approved_by_curator=admin_username,
    approved_at_curator=approved_at,
)
```

`admin_username` is read from `session.get("user", {}).get("username")` — the GitHub username of the logged-in admin curator.

## Decisions Made

- `pending_proposal` blocks with priority over `approved_mapping` — when both conditions match the same KE-WP pair (a mapping exists AND a pending proposal is open for that mapping), the pending_proposal state is shown first because it's the most actionable: flagging stale lets the curator submit fresh changes
- `flag_proposal_stale` lives in `api_bp` not `admin_bp` — regular curators (not admins) need to flag stale proposals; `@login_required` is sufficient access control
- GO proposal admin approval flow not implemented — `admin.py` currently has no GO proposal approval route; the GoMappingModel provenance update will be wired when that route is added
- `schemas.py` confidence_level already `required=True` — confirmed by test; no change needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Swapped priority order in enriched check methods**
- **Found during:** Task 1 verification test
- **Issue:** Plan spec listed "check approved mapping first, then pending proposal" — but the test expected `pending_proposal` for a pair with both a mapping and a pending proposal. The approved_mapping check was firing first, masking the pending proposal.
- **Fix:** Reordered to check pending proposals first (highest priority blocking), then approved mapping. This matches the curation workflow: if someone already has an open proposal, the right action is to flag it stale, not submit another change.
- **Files modified:** `src/core/models.py`
- **Verification:** Task 1 verification test passes with correct blocking_type in both cases
- **Committed in:** `70ff795` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 logic bug — priority ordering)
**Impact on plan:** Necessary for correct curation workflow. No scope creep.

## Issues Encountered

- Pre-existing coverage failure (37% vs 80% threshold) — all 45 tests pass, no regressions. Same issue as Plan 01, out of scope for this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Enriched `/check` and `/check_go_entry` response shapes are now stable — Plan 03 (frontend) can consume `blocking_type`, `existing`, `actions` fields
- `approved_by_curator` and `approved_at_curator` are written at every approval — Plan 03 display layer can surface this provenance
- Every new proposal row gets a UUID4 — Plan 04 (`admin_proposals.html`) can access `proposal.uuid` for display
- `is_stale` flag is settable via `/flag_proposal_stale` — Plan 03 frontend can call this endpoint from the blocking modal

---
*Phase: 02-data-model-and-audit-trail*
*Completed: 2026-02-20*
