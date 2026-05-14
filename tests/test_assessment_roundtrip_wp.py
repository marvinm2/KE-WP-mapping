"""Phase 34 (ASMT-02/07/08) — KE-WP end-to-end assessment round-trip.

HTTP path: POST /submit (with step1..step4) -> /admin/proposals/<id>/approve ->
MappingModel.get_all_mappings(). Asserts the four proposed_* columns + assessment_version
survive the proposal -> mapping handoff AND appear in the bulk-export SELECT.

Wave 0 scaffold (Plan 01). Body implemented in Plan 03 once the WP /submit handler
and admin approve path wire the four fields through.
"""
import pytest


@pytest.mark.xfail(strict=True, reason="Wired in Plan 03 — WP /submit handler + admin approve")
def test_assessment_roundtrip_wp():
    assert False, "Plan 03: implement HTTP submit -> admin approve -> get_all_mappings"
