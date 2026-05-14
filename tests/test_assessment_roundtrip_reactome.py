"""Phase 34 (ASMT-03/07/08/10) — KE-Reactome model-layer assessment round-trip.

Model-layer-direct calls per CONTEXT.md (UI deferred to Phase 37):
  db.reactome.create_proposal(..., relationship=..., basis=..., ...)
  -> db.reactome.create_approved_mapping(...)
  -> db.reactome.get_all_mappings()

Asserts:
  - All four proposed_* values survive proposal -> mapping (ASMT-03/ASMT-08).
  - REACTOME_PROPOSAL_CARRY_FIELDS is actually consumed (ASMT-10) — if the constant
    is extended but not imported, the four values silently become NULL at INSERT
    (the named Pitfall 7 in 34-RESEARCH.md).
  - assessment_version flips 'v1' -> 'v2' when any of the four answers is non-NULL.

Wave 0 scaffold (Plan 01). Body implemented in Plan 02 once the Reactome model layer
wires the new kwargs.
"""
import pytest


@pytest.mark.xfail(strict=True, reason="Wired in Plan 02 — Reactome model-layer kwargs + carry-fields use")
def test_assessment_roundtrip_reactome():
    assert False, "Plan 02: implement create_proposal -> create_approved_mapping -> get_all_mappings"
