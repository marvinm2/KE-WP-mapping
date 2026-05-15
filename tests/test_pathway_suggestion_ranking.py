"""
WP suggestion ranking regression tests — Plan 29-02.

These tests verify that after the pure-semantic shift:
  A. WP ranking order equals pure-embedding order (modulo ontology post-combine boost).
  B. A pathway with gene-only signal but embedding=0 is excluded (score below threshold).
  C. Gene-overlap chip data (matching_genes, matching_gene_count, gene_overlap_ratio) is
     still present on items that came from the gene-suggestion input.
  D. Ontology post-combine boost is applied: same embedding score but higher ontology score
     yields a higher final hybrid_score.

RED phase (pre-Task 2): Tests A and D fail on v1.4 code because _apply_ontology_boost does not
exist. After Task 2 (GREEN), all 4 tests must pass.

Failure modes expected in RED:
  - Test D: AttributeError or incorrect hybrid_score — no _apply_ontology_boost in v1.4
  - Test A: may already pass since embedding=1.0 after 29-01 YAML update; still confirmed.
"""

from src.suggestions.pathway import PathwaySuggestionService
from src.core.config_loader import ConfigLoader


# ============================================================================
# Helpers
# ============================================================================

def make_pathway_service():
    """Construct a PathwaySuggestionService with v1.5 config but no real backend."""
    # Use load_config() (reads the v1.5 YAML) rather than get_default_config()
    # (which returns v1.4 hardcoded dataclass defaults, kept for historical traceability).
    cfg = ConfigLoader.load_config()
    svc = PathwaySuggestionService(cache_model=None, embedding_service=None, config=cfg)
    return svc


def make_embedding_item(pathway_id, pathway_title, score):
    """Minimal embedding-signal item shape."""
    return {
        'pathwayID': pathway_id,
        'pathwayTitle': pathway_title,
        'confidence_score': score,
        'title_similarity': score,
        'description_similarity': 0.0,
        'embedding_similarity': score,
    }


def make_gene_item(pathway_id, pathway_title, score, genes=None):
    """Minimal gene-signal item shape (includes gene-chip fields)."""
    genes = genes or ['GENE1', 'GENE2']
    return {
        'pathwayID': pathway_id,
        'pathwayTitle': pathway_title,
        'confidence_score': score,
        'matching_genes': genes,
        'matching_gene_count': len(genes),
        'gene_overlap_ratio': round(len(genes) / 10, 2),  # assume pathway has 10 genes
    }


def make_ontology_item(pathway_id, pathway_title, score):
    """Minimal ontology-signal item shape."""
    return {
        'pathwayID': pathway_id,
        'pathwayTitle': pathway_title,
        'confidence_score': score,
    }


# ============================================================================
# Test A: Pure-embedding ordering
# ============================================================================

class TestPureEmbeddingOrder:
    """
    Test A: WP ranking order must equal pure-embedding order.

    Setup:
      P1: embedding=0.9, gene=0.0,  ontology=0.0
      P2: embedding=0.8, gene=0.95, ontology=0.0
      P3: embedding=0.7, gene=0.0,  ontology=0.6

    Under v1.5 weights (embedding=1.0, gene=0.0, ontology=0.0):
      - combine_scored_items yields: P1=0.9, P2=0.8, P3=0.7
      - _apply_ontology_boost: P3 *= (1 + 0.15*0.6) = 0.7*1.09 = 0.763
      - Final order: P1(0.9) > P2(0.8) > P3(0.763) → [P1, P2, P3]
    """

    def test_A_pure_embedding_order(self):
        svc = make_pathway_service()

        embedding_suggestions = [
            make_embedding_item('WP1', 'Pathway 1', 0.9),
            make_embedding_item('WP2', 'Pathway 2', 0.8),
            make_embedding_item('WP3', 'Pathway 3', 0.7),
        ]
        gene_suggestions = [
            make_gene_item('WP2', 'Pathway 2', 0.95, ['GENE1', 'GENE2']),
        ]
        ontology_suggestions = [
            make_ontology_item('WP3', 'Pathway 3', 0.6),
        ]

        result = svc._combine_multi_signal_suggestions(
            gene_suggestions=gene_suggestions,
            text_suggestions=[],
            embedding_suggestions=embedding_suggestions,
            ontology_suggestions=ontology_suggestions,
            limit=10,
        )

        assert len(result) == 3, f"Expected 3 results, got {len(result)}"

        ids = [r['pathwayID'] for r in result]
        assert ids == ['WP1', 'WP2', 'WP3'], (
            f"Expected order [WP1, WP2, WP3] (pure-embedding with ontology boost), got {ids}. "
            "Under v1.5: P3 gets ontology boost (0.7 * 1.09 = 0.763) but still < P2 (0.8) and < P1 (0.9)."
        )


# ============================================================================
# Test B: Gene-only signal does NOT promote
# ============================================================================

class TestGeneOnlySignalExcluded:
    """
    Test B: A pathway with gene=0.95 but embedding=0.0 and ontology=0.0
    has hybrid_score=0.0 under embedding-only weighting and is excluded
    by the base_threshold (0.15).
    """

    def test_B_gene_only_excluded(self):
        svc = make_pathway_service()

        gene_suggestions = [
            make_gene_item('WP_GENE_ONLY', 'Gene-only Pathway', 0.95, ['GENE1', 'GENE2', 'GENE3']),
        ]
        # No embedding, no ontology for WP_GENE_ONLY
        embedding_suggestions = [
            make_embedding_item('WP_OTHER', 'Other Pathway', 0.80),
        ]
        ontology_suggestions = []

        result = svc._combine_multi_signal_suggestions(
            gene_suggestions=gene_suggestions,
            text_suggestions=[],
            embedding_suggestions=embedding_suggestions,
            ontology_suggestions=ontology_suggestions,
            limit=10,
        )

        result_ids = {r['pathwayID'] for r in result}
        assert 'WP_GENE_ONLY' not in result_ids, (
            "WP_GENE_ONLY should be excluded: gene weight=0.0 so hybrid_score=0.0 < base_threshold=0.15"
        )
        assert 'WP_OTHER' in result_ids, (
            "WP_OTHER (embedding=0.80) should still appear"
        )


# ============================================================================
# Test C: Gene chip data still present on results
# ============================================================================

class TestGeneChipDataPresent:
    """
    Test C: Items that came from gene-suggestion input must carry
    matching_genes, matching_gene_count, and gene_overlap_ratio — even though
    those values did not influence rank under v1.5.
    """

    def test_C_gene_chip_data_on_result_items(self):
        svc = make_pathway_service()

        expected_genes = ['MAPK1', 'TP53', 'BRCA1']
        gene_suggestions = [
            make_gene_item('WP100', 'Apoptosis', 0.6, expected_genes),
        ]
        # WP100 also has an embedding signal (so it passes threshold)
        embedding_suggestions = [
            make_embedding_item('WP100', 'Apoptosis', 0.75),
        ]
        ontology_suggestions = []

        result = svc._combine_multi_signal_suggestions(
            gene_suggestions=gene_suggestions,
            text_suggestions=[],
            embedding_suggestions=embedding_suggestions,
            ontology_suggestions=ontology_suggestions,
            limit=10,
        )

        wp100 = next((r for r in result if r['pathwayID'] == 'WP100'), None)
        assert wp100 is not None, "WP100 should be in the result"

        assert 'matching_genes' in wp100, "matching_genes key missing from result item"
        assert 'matching_gene_count' in wp100, "matching_gene_count key missing from result item"
        assert 'gene_overlap_ratio' in wp100, "gene_overlap_ratio key missing from result item"

        assert wp100['matching_genes'] == expected_genes, (
            f"matching_genes mismatch: {wp100['matching_genes']} != {expected_genes}"
        )
        assert wp100['matching_gene_count'] == len(expected_genes), (
            f"matching_gene_count mismatch: {wp100['matching_gene_count']} != {len(expected_genes)}"
        )


# ============================================================================
# Test D: Ontology post-combine boost applied
# ============================================================================

class TestOntologyPostCombineBoost:
    """
    Test D: When two pathways have identical embedding scores but one has an
    ontology match, the ontology post-combine boost must lift its hybrid_score.

    Setup:
      P1: embedding=0.5, ontology=0.0  → boosted hybrid = 0.5 * (1 + 0.15*0.0) = 0.5
      P2: embedding=0.5, ontology=1.0  → boosted hybrid = 0.5 * (1 + 0.15*1.0) = 0.575

    Expected: P2 > P1 in ranking, P2.hybrid_score ≈ 0.575 (within 1e-6).
    """

    def test_D_ontology_boost_applied(self):
        svc = make_pathway_service()

        embedding_suggestions = [
            make_embedding_item('WP_P1', 'Pathway No-Ontology', 0.5),
            make_embedding_item('WP_P2', 'Pathway With-Ontology', 0.5),
        ]
        ontology_suggestions = [
            make_ontology_item('WP_P2', 'Pathway With-Ontology', 1.0),
        ]

        result = svc._combine_multi_signal_suggestions(
            gene_suggestions=[],
            text_suggestions=[],
            embedding_suggestions=embedding_suggestions,
            ontology_suggestions=ontology_suggestions,
            limit=10,
        )

        assert len(result) == 2, f"Expected 2 results, got {len(result)}"

        p1 = next((r for r in result if r['pathwayID'] == 'WP_P1'), None)
        p2 = next((r for r in result if r['pathwayID'] == 'WP_P2'), None)

        assert p1 is not None, "WP_P1 missing from result"
        assert p2 is not None, "WP_P2 missing from result"

        assert p2['hybrid_score'] > p1['hybrid_score'], (
            f"P2 (ontology boost) should rank above P1: P2={p2['hybrid_score']}, P1={p1['hybrid_score']}"
        )

        # P2 expected = 0.5 * (1 + 0.15 * 1.0) = 0.575
        expected_p2 = 0.5 * (1 + 0.15 * 1.0)
        assert abs(p2['hybrid_score'] - expected_p2) < 1e-4, (
            f"P2 hybrid_score should be ~{expected_p2}, got {p2['hybrid_score']}"
        )

        # P2 should rank first
        assert result[0]['pathwayID'] == 'WP_P2', (
            f"WP_P2 (ontology-boosted) should rank first, got {result[0]['pathwayID']}"
        )
