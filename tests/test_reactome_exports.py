"""Unit tests for Reactome GMT generators (Phase 26 / plan 26-03).

Covers:
- _load_reactome_annotations file IO + missing-file fallback
- generate_ke_reactome_gmt per-mapping row format, dedup, confidence filter,
  empty input, and the no-direction-suffix invariant (Reactome has no direction).
- generate_ke_centric_reactome_gmt KE grouping, gene union/dedup, numeric KE
  sort, and confidence filter.
"""
import json

import pytest

from src.exporters.gmt_exporter import (
    _load_reactome_annotations,
    generate_ke_centric_reactome_gmt,
    generate_ke_reactome_gmt,
)


@pytest.fixture
def gene_annotations_file(tmp_path):
    """Tiny Reactome gene-annotations JSON fixture written to a tmp path.

    Overlap on TP53 between R-HSA-100 and R-HSA-200 lets us exercise dedup.
    R-HSA-999 is intentionally absent to exercise the missing-genes skip path.
    """
    annotations = {
        "R-HSA-100": ["TP53", "MDM2", "ATM"],
        "R-HSA-200": ["TP53", "BRCA1", "BRCA2"],  # overlaps with 100 on TP53
        "R-HSA-300": ["EGFR"],
    }
    path = tmp_path / "reactome_gene_annotations.json"
    path.write_text(json.dumps(annotations))
    return str(path)


@pytest.fixture
def sample_mappings():
    return [
        {
            "uuid": "u1",
            "ke_id": "KE 1",
            "ke_title": "Apoptosis",
            "reactome_id": "R-HSA-100",
            "pathway_name": "p53 signaling",
            "confidence_level": "High",
        },
        {
            "uuid": "u2",
            "ke_id": "KE 1",
            "ke_title": "Apoptosis",
            "reactome_id": "R-HSA-200",
            "pathway_name": "DNA repair",
            "confidence_level": "Medium",
        },
        {
            "uuid": "u3",
            "ke_id": "KE 5",
            "ke_title": "Cell proliferation",
            "reactome_id": "R-HSA-300",
            "pathway_name": "EGFR pathway",
            "confidence_level": "Low",
        },
        {
            "uuid": "u4",
            "ke_id": "KE 7",
            "ke_title": "Unmapped",
            "reactome_id": "R-HSA-999",
            "pathway_name": "Missing genes",
            "confidence_level": "High",
        },
    ]


# ---- _load_reactome_annotations ----------------------------------------------


def test_load_reactome_annotations_default_missing(tmp_path):
    out = _load_reactome_annotations(path=str(tmp_path / "nope.json"))
    assert out == {}


def test_load_reactome_annotations_reads_file(gene_annotations_file):
    out = _load_reactome_annotations(path=gene_annotations_file)
    assert "R-HSA-100" in out
    assert out["R-HSA-100"] == ["TP53", "MDM2", "ATM"]


# ---- generate_ke_reactome_gmt (per-mapping) ----------------------------------


def test_generate_ke_reactome_gmt_basic(sample_mappings, gene_annotations_file):
    out = generate_ke_reactome_gmt(sample_mappings, gene_annotations_path=gene_annotations_file)
    lines = [l for l in out.split("\n") if l]
    # u4 has no genes for R-HSA-999, so it is silently skipped -> 3 lines
    assert len(lines) == 3
    # Every line has >=3 tab-separated tokens (term, desc, >=1 gene)
    for l in lines:
        assert len(l.split("\t")) >= 3
    # First line shape: "KE1_..._R-HSA-100\tp53 signaling\tTP53\tMDM2\tATM"
    first = lines[0].split("\t")
    assert first[0].startswith("KE1_")
    assert first[0].endswith("_R-HSA-100")
    assert first[1] == "p53 signaling"
    assert "TP53" in first[2:]


def test_generate_ke_reactome_gmt_no_direction_suffix(sample_mappings, gene_annotations_file):
    out = generate_ke_reactome_gmt(sample_mappings, gene_annotations_path=gene_annotations_file)
    # Reactome must not emit "| direction:" anywhere (D-05).
    assert "| direction:" not in out


def test_generate_ke_reactome_gmt_min_confidence(sample_mappings, gene_annotations_file):
    out = generate_ke_reactome_gmt(
        sample_mappings, gene_annotations_path=gene_annotations_file, min_confidence="high"
    )
    lines = [l for l in out.split("\n") if l]
    # u1 (High) has genes; u4 (High) has no genes and is skipped -> 1 line
    assert len(lines) == 1
    assert "p53 signaling" in lines[0]


def test_generate_ke_reactome_gmt_empty():
    assert generate_ke_reactome_gmt([]) == ""


# ---- generate_ke_centric_reactome_gmt ----------------------------------------


def test_generate_ke_centric_reactome_gmt_unions_genes(sample_mappings, gene_annotations_file):
    out = generate_ke_centric_reactome_gmt(
        sample_mappings, gene_annotations_path=gene_annotations_file
    )
    lines = [l for l in out.split("\n") if l]
    # KE 1 has u1+u2 (3+3 genes, 1 overlap -> 5 unique); KE 5 has u3 (1 gene);
    # KE 7 has no genes -> skipped. Expect 2 lines.
    assert len(lines) == 2
    ke1 = next(l for l in lines if l.startswith("KE1\t"))
    ke1_tokens = ke1.split("\t")
    assert ke1_tokens[0] == "KE1"
    assert ke1_tokens[1] == "Apoptosis"
    # Genes deduplicated: TP53 should appear exactly once
    gene_tokens = ke1_tokens[2:]
    assert gene_tokens.count("TP53") == 1
    assert set(gene_tokens) == {"TP53", "MDM2", "ATM", "BRCA1", "BRCA2"}


def test_generate_ke_centric_reactome_gmt_sorts_by_ke_number(sample_mappings, gene_annotations_file):
    out = generate_ke_centric_reactome_gmt(
        sample_mappings, gene_annotations_path=gene_annotations_file
    )
    lines = [l for l in out.split("\n") if l]
    # KE1 must come before KE5 in numeric order
    assert lines[0].startswith("KE1\t")
    assert lines[1].startswith("KE5\t")


def test_generate_ke_centric_reactome_gmt_min_confidence(sample_mappings, gene_annotations_file):
    out = generate_ke_centric_reactome_gmt(
        sample_mappings, gene_annotations_path=gene_annotations_file, min_confidence="medium"
    )
    lines = [l for l in out.split("\n") if l]
    # Only u2 (Medium) survives the filter -> KE 1 with BRCA1/BRCA2/TP53
    assert len(lines) == 1
    assert lines[0].startswith("KE1\t")
