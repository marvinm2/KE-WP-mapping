---
status: resolved
trigger: "Admin users submitting via the curator proposal form get their mapping created immediately without a separate admin approval step. The resulting mapping has null provenance (approved_by, approved_at, suggestion_score all null)."
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T12:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - The /submit route in api.py calls mapping_model.create_mapping() directly for any logged-in user including admins, bypassing the proposal workflow entirely. The /submit_proposal route does exist but is a separate endpoint for revisions; the main curator form POSTs to /submit.
test: Read api.py submit() and submit_proposal() handlers; read index.html for form action target
expecting: Confirmed - /submit calls create_mapping directly with no is_admin gate and no proposal creation
next_action: DONE - diagnosis complete

## Symptoms

expected: Curator proposal form always creates a proposal record (pending state) regardless of submitter role; a separate admin approval action creates the mapping with provenance
actual: Admin users submitting via the curator proposal form get their mapping created immediately without a separate admin approval step; resulting mapping has null provenance (approved_by, approved_at, suggestion_score all null)
errors: No runtime error - silent wrong-path execution producing null provenance fields
reproduction: Log in as admin user, submit curator proposal form, observe mapping created immediately with null approved_by/approved_at/suggestion_score
started: Unknown - UAT discovery

## Eliminated

- hypothesis: The submission route checks is_admin and takes an explicit conditional shortcut
  evidence: No is_admin check exists anywhere in api.py; the bypass is unconditional for all users
  timestamp: 2026-02-21

- hypothesis: The bypass is in the template (admin-specific form action or hidden field)
  evidence: index.html contains no is_admin, admin, or curator-specific form logic
  timestamp: 2026-02-21

## Evidence

- timestamp: 2026-02-21
  checked: src/blueprints/api.py lines 111-175 (/submit route)
  found: The /submit route calls mapping_model.create_mapping() directly (line 155) for any authenticated user with no proposal creation, no is_admin check, and no provenance fields set (approved_by_curator, approved_at_curator, suggestion_score all absent from this call)
  implication: Every new mapping submitted through the curator form is created immediately as a bare mapping row regardless of the submitter's role

- timestamp: 2026-02-21
  checked: src/blueprints/api.py lines 468-581 (/submit_proposal route)
  found: /submit_proposal creates a proposal record (status=pending) but handles only revisions to EXISTING mappings - it calls proposal_model.find_mapping_by_details() (line 542) and returns 404 if not found; it is not reachable for new mappings
  implication: New mapping submissions have no path through the proposal workflow at all

- timestamp: 2026-02-21
  checked: src/core/models.py MappingModel.create_mapping() lines 534-583
  found: create_mapping() accepts no provenance parameters (approved_by_curator, approved_at_curator, suggestion_score); it inserts a row with only ke_id, ke_title, wp_id, wp_title, connection_type, confidence_level, created_by, uuid - all provenance columns remain NULL
  implication: Any mapping created via /submit will always have null provenance; there is no way to populate provenance through this path

- timestamp: 2026-02-21
  checked: src/blueprints/admin.py approve_proposal() lines 214-311
  found: The correct provenance path exists here: approve_proposal() calls mapping_model.update_mapping() with approved_by_curator, approved_at_curator, and suggestion_score (lines 274-282) after validating admin session
  implication: Provenance is only populated when admin explicitly approves a proposal through the admin dashboard - this path is never reached for new submissions

- timestamp: 2026-02-21
  checked: templates/index.html
  found: No is_admin, admin, or curator-specific logic in the template; the form action and JS submit path are identical for all users
  implication: The bypass is entirely server-side in the /submit route, not gated or differentiated in the template

## Resolution

root_cause: The /submit endpoint in src/blueprints/api.py (lines 154-167) calls mapping_model.create_mapping() directly for all authenticated users, including admins, creating a bare mapping row with null provenance instead of routing through the proposal workflow; there is no is_admin check and no proposal creation in this path.
fix: (diagnosis only - not applied)
verification: (diagnosis only - not applied)
files_changed: []
