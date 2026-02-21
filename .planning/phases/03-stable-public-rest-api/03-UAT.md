---
status: resolved
phase: 03-stable-public-rest-api
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-02-21T00:00:00Z
updated: 2026-02-21T12:00:00Z
---

## Current Test

number: 7
name: Suggestion score flows through approval
expected: |
  [testing complete]
awaiting: n/a

## Tests

### 1. List KE-WP mappings without authentication
expected: |
  Start the dev server (python app.py), then in a new terminal run:
    curl http://localhost:5000/api/v1/mappings
  Without logging in, you should receive a JSON response with two top-level keys:
  "data" (an array of mapping objects) and "pagination" (with fields: page, per_page, total, total_pages, next, prev).
  No 401 or redirect to login.
result: pass

### 2. Filter KE-WP mappings by ke_id
expected: |
  If you have any approved mappings, pick a KE ID from one (e.g. from the explore page or from test 1's data output). Then run:
    curl "http://localhost:5000/api/v1/mappings?ke_id=<your_ke_id>"
  The response "data" array should contain only mappings for that KE. The pagination.total should be smaller than the unfiltered total.
  If no mappings exist yet, skip this test.
result: pass

### 3. Single KE-WP mapping detail and 404
expected: |
  Pick a UUID from any mapping in the data from test 1. Run:
    curl http://localhost:5000/api/v1/mappings/<uuid>
  Should return a single mapping object (not an array). Then test with a fake UUID:
    curl http://localhost:5000/api/v1/mappings/00000000-0000-0000-0000-000000000000
  Should return a JSON response with an "error" key and HTTP 404 status.
result: pass

### 4. List KE-GO mappings without authentication
expected: |
  Run:
    curl http://localhost:5000/api/v1/go-mappings
  Should return a JSON response with "data" and "pagination" keys, same envelope shape as /api/v1/mappings.
  No authentication required.
result: pass

### 5. CSV content negotiation
expected: |
  Run:
    curl -H "Accept: text/csv" http://localhost:5000/api/v1/mappings
  The response should be plain CSV text (not JSON) with a header row as the first line.
  The Content-Type response header should be text/csv.
  You can verify the header row with: curl -H "Accept: text/csv" http://localhost:5000/api/v1/mappings | head -1
result: pass

### 6. CORS header present
expected: |
  Run:
    curl -v http://localhost:5000/api/v1/mappings 2>&1 | grep -i "access-control"
  The response headers should include:
    Access-Control-Allow-Origin: *
  This allows browser-based scripts from any origin to call the API.
result: pass

### 7. Suggestion score flows through approval
expected: |
  Admin submitting via the curator proposal form should create a proposal requiring a separate
  approval step. At approval time, approved_by, approved_at, and suggestion_score are written
  to the mapping row. The mapping should NOT appear immediately without an approval step.
result: issue
reported: "Used curator proposal form as admin — mapping appeared directly in the table without a separate admin approval step, and the mapping has null provenance (approved_by, approved_at, suggestion_score all null)"
severity: major

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Admin submitting via the curator proposal form creates a proposal requiring a separate admin approval step; the mapping does not appear until explicitly approved, and approved_by/approved_at/suggestion_score are written at approval time"
  status: resolved
  reason: "User reported: Used curator proposal form as admin — mapping appeared directly in the table without a separate admin approval step, and the mapping has null provenance (approved_by, approved_at, suggestion_score all null)"
  severity: major
  test: 7
  root_cause: "The /submit endpoint in src/blueprints/api.py (lines 154-163) calls mapping_model.create_mapping() directly for ALL authenticated users with no proposal creation and no provenance parameters — admin approval via approve_proposal() is therefore never reachable for new-pair submissions"
  artifacts:
    - path: "src/blueprints/api.py"
      issue: "/submit calls create_mapping() directly, bypassing proposal creation and provenance; /submit_proposal 404s on new pairs"
    - path: "src/core/models.py"
      issue: "MappingModel.create_mapping() has no provenance parameters (approved_by_curator, approved_at_curator, suggestion_score)"
  missing:
    - "/submit must create a proposal record (status=pending) instead of calling create_mapping() directly"
    - "ProposalModel.create_proposal() or a new method must handle new-pair submissions (currently /submit_proposal returns 404 if no existing mapping found)"
    - "approve_proposal() in admin.py remains the sole path that populates provenance — no changes needed there"
  debug_session: ".planning/debug/admin-bypass-curator-proposal.md"
