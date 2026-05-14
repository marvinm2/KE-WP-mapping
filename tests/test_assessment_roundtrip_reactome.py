"""Phase 34 (ASMT-03/07/08/10) — KE-Reactome model-layer assessment round-trip.

Model-layer-direct calls per CONTEXT.md (UI deferred to Phase 37):
  ReactomeProposalModel(...).create_new_pair_reactome_proposal(..., proposed_relationship=..., ...)
  -> ReactomeMappingModel(...).create_approved_mapping(proposal_id=..., approved_by_curator=...)
  -> ReactomeMappingModel(...).get_all_mappings()

Asserts:
  - All four proposed_* values survive proposal -> mapping (ASMT-03/ASMT-08).
  - REACTOME_PROPOSAL_CARRY_FIELDS is actually consumed (ASMT-10) — if the constant
    is extended but not imported, the four values silently become NULL at INSERT
    (the named Pitfall 7 in 34-RESEARCH.md).
  - assessment_version flips 'v1' -> 'v2' when any of the four answers is non-NULL.
"""
import inspect

import pytest

from src.core.models import (
    Database,
    ReactomeMappingModel,
    ReactomeProposalModel,
)


def test_assessment_roundtrip_reactome(tmp_path):
    """ASMT-03/07/08/10 — model-layer round trip on Reactome path.

    Creates a proposal with all four assessment answers, approves it via
    create_approved_mapping, reads via get_all_mappings, and asserts all
    four values plus assessment_version='v2' survive the round trip.
    """
    db = Database(str(tmp_path / "test.db"))
    proposal_model = ReactomeProposalModel(db)
    mapping_model = ReactomeMappingModel(db)

    proposal_id = proposal_model.create_new_pair_reactome_proposal(
        ke_id="KE:100",
        ke_title="t",
        reactome_id="R-HSA-1",
        pathway_name="p",
        species="Homo sapiens",
        confidence_level="high",
        provider_username="github:test",
        suggestion_score=0.9,
        proposed_relationship="causative",
        proposed_basis="known",
        proposed_specificity="specific",
        proposed_coverage="complete",
    )
    assert isinstance(proposal_id, int), (
        f"create_new_pair_reactome_proposal should return int, got: {proposal_id!r}"
    )

    new_mapping_id = mapping_model.create_approved_mapping(
        proposal_id=proposal_id,
        approved_by_curator="github:admin",
    )
    assert new_mapping_id is not None, (
        "create_approved_mapping returned None — check IntegrityError or DB error"
    )

    rows = mapping_model.get_all_mappings()
    assert len(rows) == 1
    row = rows[0]
    assert row["proposed_relationship"] == "causative"
    assert row["proposed_basis"] == "known"
    assert row["proposed_specificity"] == "specific"
    assert row["proposed_coverage"] == "complete"
    assert row["assessment_version"] == "v2"
    # Prove the rest of the carry path is intact
    assert row["ke_id"] == "KE:100"
    assert row["reactome_id"] == "R-HSA-1"
    assert row["uuid"] is not None


def test_assessment_legacy_v1_reactome(tmp_path):
    """A proposal with no assessment answers approves into a 'v1' mapping
    (per CONTEXT.md model-layer rule: any non-NULL => 'v2'; else 'v1').
    """
    db = Database(str(tmp_path / "test.db"))
    proposal_model = ReactomeProposalModel(db)
    mapping_model = ReactomeMappingModel(db)

    proposal_id = proposal_model.create_new_pair_reactome_proposal(
        ke_id="KE:200",
        ke_title="t",
        reactome_id="R-HSA-2",
        pathway_name="p",
        species="Homo sapiens",
        confidence_level="low",
        provider_username="github:test",
        suggestion_score=0.1,
        # All four assessment kwargs omitted; defaults to None
    )
    assert isinstance(proposal_id, int)

    mapping_model.create_approved_mapping(
        proposal_id=proposal_id,
        approved_by_curator="github:admin",
    )
    rows = mapping_model.get_all_mappings()
    assert rows[0]["assessment_version"] == "v1"
    for col in ("proposed_relationship", "proposed_basis",
                "proposed_specificity", "proposed_coverage"):
        assert rows[0][col] is None


def test_carry_fields_constant_actually_used():
    """ASMT-10: REACTOME_PROPOSAL_CARRY_FIELDS must be referenced inside
    create_approved_mapping — not just defined and ignored. Phase 34 fixes
    the v1.4 dead-constant tech-debt. If this test fails, Plan 02 Task 2
    extended the constant but did not wire it into the INSERT."""
    src = inspect.getsource(ReactomeMappingModel.create_approved_mapping)
    assert "REACTOME_PROPOSAL_CARRY_FIELDS" in src, (
        "create_approved_mapping must reference the carry-fields constant "
        "(ASMT-10); see 34-RESEARCH.md Pitfall 7."
    )
