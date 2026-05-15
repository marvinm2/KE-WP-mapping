"""
Unit tests pinning the ReactomeSuggestionService._combine_reactome_scores()
contract under v1.5 pure-semantic (embedding-only) ranking.

Tests A-D prove:
  A. Rank order = pure-embedding order (highest embedding → first result)
  B. Gene overlap data (gene_overlap, matching_genes, reactome_pathway_gene_count)
     is still propagated on every item — used by the frontend chip
  C. Gene-only signal with text_similarity=0.0 → excluded (hybrid_score=0 fails threshold)
  D. No multi_evidence_bonus residue: item with both signals present still scores
     exactly embedding_weight * text_similarity (old +0.05 bonus is gone)
"""
import pytest
from unittest.mock import patch


# ============================================================================
# Fixtures
# ============================================================================

def _emb(reactome_id, text_similarity, name_similarity=None, definition_similarity=None):
    """Build a minimal embedding-scored Reactome item (shape from _compute_embedding_scores)."""
    item = {
        'reactome_id': reactome_id,
        'pathway_name': f'Test Pathway {reactome_id}',
        'text_similarity': text_similarity,
    }
    if name_similarity is not None:
        item['name_similarity'] = name_similarity
        item['definition_similarity'] = definition_similarity or 0.0
    return item


def _gene(reactome_id, gene_overlap, matching_genes=None, reactome_pathway_gene_count=30):
    """Build a minimal gene-scored Reactome item (shape from _compute_gene_overlap_scores)."""
    return {
        'reactome_id': reactome_id,
        'pathway_name': f'Test Pathway {reactome_id}',
        'text_similarity': 0.0,
        'gene_overlap': gene_overlap,
        'matching_genes': matching_genes or ['TP53'],
        'reactome_pathway_gene_count': reactome_pathway_gene_count,
        'hybrid_score': gene_overlap,
        'match_types': ['gene'],
    }


def _make_svc():
    """
    Build a ReactomeSuggestionService with loading disabled.

    Patches the data-loading methods so no NPZ/JSON files are required
    at test time. Config is loaded via ConfigLoader.load_config() which
    reads scoring_config.yaml (v1.5 values: embedding=1.0, gene=0.0, bonus=0.0).
    Note: get_default_config() returns dataclass defaults (v1.4), so load_config()
    is required to get the YAML v1.5 values.
    """
    from src.core.config_loader import ConfigLoader

    cfg = ConfigLoader.load_config()

    with patch.object(
        __import__('src.suggestions.reactome', fromlist=['ReactomeSuggestionService'])
        .ReactomeSuggestionService,
        '_load_npz_into',
        return_value=None,
    ), patch.object(
        __import__('src.suggestions.reactome', fromlist=['ReactomeSuggestionService'])
        .ReactomeSuggestionService,
        '_load_json_into',
        return_value=None,
    ):
        from src.suggestions.reactome import ReactomeSuggestionService
        svc = ReactomeSuggestionService(
            config=cfg,
            embedding_service=None,
            cache_model=None,
        )
    return svc


# ============================================================================
# Tests
# ============================================================================

class TestReactomePureEmbeddingRanking:
    """Pin ReactomeSuggestionService._combine_reactome_scores() under v1.5 weights."""

    def test_A_pure_embedding_rank_order(self):
        """
        Test A (pure-embedding ordering): embedding=[R-001 0.95, R-002 0.90, R-003 0.85],
        gene=[R-001 0.0, R-002 0.95, R-003 0.0].

        Values are above the v1.5 reactome_suggestion.min_threshold (0.83 per
        scoring_config.yaml after the Phase 30-01 calibration), so all three
        items pass the post-combine threshold filter.

        After _combine_reactome_scores, rank order must be [R-001, R-002, R-003]
        — i.e. driven solely by text_similarity, NOT by gene_overlap.
        """
        svc = _make_svc()

        embedding_scores = [
            _emb('R-HSA-001', 0.95),
            _emb('R-HSA-002', 0.90),
            _emb('R-HSA-003', 0.85),
        ]
        gene_scores = [
            _gene('R-HSA-001', 0.0),
            _gene('R-HSA-002', 0.95),
            _gene('R-HSA-003', 0.0),
        ]

        results = svc._combine_reactome_scores(embedding_scores, gene_scores)

        assert len(results) >= 3, f"Expected at least 3 results, got {len(results)}"

        ids = [r['reactome_id'] for r in results[:3]]
        assert ids == ['R-HSA-001', 'R-HSA-002', 'R-HSA-003'], (
            f"Expected embedding-driven order [R-001, R-002, R-003], got {ids}. "
            "Gene overlap (R-002=0.95) must NOT affect rank order under v1.5 weights."
        )

    def test_B_gene_overlap_data_propagated(self):
        """
        Test B (gene data still on items): R-002 has gene_overlap=0.95, matching_genes=['TP53'],
        reactome_pathway_gene_count=30. These must all appear on the result item even though
        gene signal doesn't affect rank. Embedding values are above the
        post-combine min_threshold (0.83) so the items survive filtering.
        """
        svc = _make_svc()

        embedding_scores = [
            _emb('R-HSA-001', 0.95),
            _emb('R-HSA-002', 0.90),
        ]
        gene_scores = [
            _gene('R-HSA-002', 0.95, matching_genes=['TP53'], reactome_pathway_gene_count=30),
        ]

        results = svc._combine_reactome_scores(embedding_scores, gene_scores)

        r002 = next((r for r in results if r['reactome_id'] == 'R-HSA-002'), None)
        assert r002 is not None, "R-HSA-002 not found in results"

        assert r002.get('gene_overlap', None) == pytest.approx(0.95, abs=1e-4), (
            f"gene_overlap should be 0.95, got {r002.get('gene_overlap')}"
        )
        assert 'TP53' in r002.get('matching_genes', []), (
            f"matching_genes should contain 'TP53', got {r002.get('matching_genes')}"
        )
        assert r002.get('reactome_pathway_gene_count') == 30, (
            f"reactome_pathway_gene_count should be 30, got {r002.get('reactome_pathway_gene_count')}"
        )

    def test_C_gene_only_excluded_by_threshold(self):
        """
        Test C (gene-only signal excluded by min_threshold): An item with
        text_similarity=0.0 and gene_overlap=0.95 yields hybrid_score=0.0
        under v1.5 weights (gene=0.0) and must be excluded by min_threshold.
        """
        svc = _make_svc()

        embedding_scores = []   # No embedding signal for this ID
        gene_scores = [
            _gene('R-HSA-GENE-ONLY', 0.95, matching_genes=['BRCA1']),
        ]

        results = svc._combine_reactome_scores(embedding_scores, gene_scores)

        gene_only_ids = [r['reactome_id'] for r in results]
        assert 'R-HSA-GENE-ONLY' not in gene_only_ids, (
            "Item with text_similarity=0.0 should be excluded (hybrid_score=0.0 "
            "fails min_threshold) under v1.5 pure-embedding weights."
        )

    def test_D_no_multi_evidence_bonus(self):
        """
        Test D (no multi_evidence_bonus): An item with text_similarity=0.9 and
        gene_overlap=0.5. Under v1.5 weights (embedding=1.0, gene=0.0, bonus=0.0):
          hybrid_score = 0.9 * 1.0 + 0.5 * 0.0 = 0.9 exactly.
        NOT 0.95 (which would indicate the old +0.05 multi_evidence_bonus leaked in).

        text_similarity is set above min_threshold (0.83) so the item survives
        the post-combine filter.
        """
        svc = _make_svc()

        embedding_scores = [_emb('R-HSA-BOTH', 0.9)]
        gene_scores = [_gene('R-HSA-BOTH', 0.5, matching_genes=['TP53'])]

        results = svc._combine_reactome_scores(embedding_scores, gene_scores)

        r_both = next((r for r in results if r['reactome_id'] == 'R-HSA-BOTH'), None)
        assert r_both is not None, "R-HSA-BOTH should appear in results (hybrid_score=0.9 > threshold)"

        expected = 0.9  # text_similarity * 1.0 + gene_overlap * 0.0
        assert abs(r_both['hybrid_score'] - expected) < 1e-4, (
            f"hybrid_score should be exactly {expected} (no multi_evidence_bonus), "
            f"got {r_both['hybrid_score']}. Old +0.05 bonus may have leaked in."
        )
