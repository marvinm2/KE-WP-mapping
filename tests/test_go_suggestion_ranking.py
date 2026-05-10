"""
GO suggestion ranking regression tests — v1.5 pure-semantic contract.

These tests pin the v1.5 contract; refactor in Task 2 must keep them green.

Tests A–E confirm that:
  - GO BP / MF ranking is driven by BioBERT embedding similarity only (SEMRANK-02)
  - Gene-overlap data is still computed and surfaced on each item (chip display)
  - IC boost (post-combine) still operates correctly on the final hybrid_score
  - Gene-only signal does NOT promote items past the min_threshold

Plans 29-02 and 29-04 can rely on these contracts without re-testing them.
"""
import pytest
from src.suggestions.go import GoSuggestionService, _NamespaceData
from src.core.config_loader import ConfigLoader


# ============================================================================
# Fixtures
# ============================================================================

def make_embedding_item(go_id, go_name, text_similarity,
                        name_similarity=None, definition_similarity=None):
    """Build a fake embedding-scored GO item."""
    item = {
        'go_id': go_id,
        'go_name': go_name,
        'text_similarity': text_similarity,
        'hybrid_score': text_similarity,
        'match_types': ['text'],
        'name_similarity': name_similarity if name_similarity is not None else text_similarity,
        'definition_similarity': definition_similarity if definition_similarity is not None else 0.0,
        'quickgo_link': f"https://www.ebi.ac.uk/QuickGO/term/{go_id}",
    }
    return item


def make_gene_item(go_id, go_name, gene_overlap, matching_genes=None, go_gene_count=10):
    """Build a fake gene-overlap-scored GO item."""
    return {
        'go_id': go_id,
        'go_name': go_name,
        'gene_overlap': gene_overlap,
        'matching_genes': matching_genes or [],
        'go_gene_count': go_gene_count,
        'hybrid_score': gene_overlap,
        'match_types': ['gene'],
        'text_similarity': 0.0,
        'quickgo_link': f"https://www.ebi.ac.uk/QuickGO/term/{go_id}",
    }


def make_ns_data_for(namespace: str):
    """
    Build a minimal _NamespaceData for the given namespace ('go_bp' or 'go_mf').

    Uses real config (post-29-01 v1.5 YAML) with empty embeddings, metadata,
    annotations, and hierarchy so no file I/O is required.

    load_config() is used (not get_default_config()) because the v1.5 weights
    live in the YAML file — get_default_config() returns the dataclass defaults
    which still carry the v1.4 values (0.55/0.45/0.05) as historical documentation.
    """
    cfg = ConfigLoader.load_config()
    go_config = getattr(cfg, namespace)  # cfg.go_bp or cfg.go_mf
    return _NamespaceData(
        embeddings={},
        name_embeddings={},
        metadata={},
        annotations={},
        hierarchy={},
        config=go_config,
    )


def make_service():
    """Create a GoSuggestionService that does NOT load any disk files."""
    return GoSuggestionService(
        cache_model=None,
        embedding_service=None,
        ke_override_model=None,
        # Point all file paths at non-existent files so graceful-degradation fires
        go_embeddings_path='',
        go_name_embeddings_path='',
        go_metadata_path='',
        go_annotations_path='',
        go_mf_embeddings_path='',
        go_mf_name_embeddings_path='',
        go_mf_metadata_path='',
        go_mf_annotations_path='',
        go_mf_hierarchy_path='',
    )


# ============================================================================
# Test A — GO BP pure-embedding ordering
# ============================================================================

class TestGoBPPureEmbeddingOrdering:
    """Test A: BP ranking order is determined by text_similarity, not gene_overlap."""

    def test_a_bp_pure_embedding_ranking(self):
        """
        Under v1.5 weights (embedding=1.0, gene=0.0), GO:001 (text_similarity=0.9)
        must rank above GO:002 (text_similarity=0.8) even when GO:002 has high
        gene_overlap (0.95). Under v1.4 (0.55/0.45), GO:002 would have ranked first.
        """
        embedding_scores = [
            make_embedding_item('GO:0000001', 'Apoptosis', 0.9),
            make_embedding_item('GO:0000002', 'Cell death', 0.8),
            make_embedding_item('GO:0000003', 'DNA repair', 0.7),
        ]
        gene_scores = [
            make_gene_item('GO:0000001', 'Apoptosis', 0.0),
            make_gene_item('GO:0000002', 'Cell death', 0.95, matching_genes=['TP53', 'CASP3']),
            make_gene_item('GO:0000003', 'DNA repair', 0.0),
        ]

        ns_data = make_ns_data_for('go_bp')
        service = make_service()

        result = service._combine_go_scores_for(embedding_scores, gene_scores, ns_data)

        # Result must be in embedding-similarity order: GO:001, GO:002, GO:003
        assert len(result) >= 2, "Expected at least 2 items above threshold"

        go_ids = [item['go_id'] for item in result]
        assert go_ids.index('GO:0000001') < go_ids.index('GO:0000002'), (
            f"GO:0000001 (text_sim=0.9) must rank above GO:0000002 (text_sim=0.8), "
            f"but got order: {go_ids}"
        )
        if 'GO:0000003' in go_ids:
            assert go_ids.index('GO:0000002') < go_ids.index('GO:0000003'), (
                f"GO:0000002 (text_sim=0.8) must rank above GO:0000003 (text_sim=0.7)"
            )


# ============================================================================
# Test B — GO MF pure-embedding ordering
# ============================================================================

class TestGoMFPureEmbeddingOrdering:
    """Test B: MF ranking order is determined by text_similarity, not gene_overlap."""

    def test_b_mf_pure_embedding_ranking(self):
        """
        Same scenario as Test A but for MF namespace. Verifies mf config is also
        v1.5 (embedding=1.0, gene=0.0) and produces embedding-driven order.
        """
        embedding_scores = [
            make_embedding_item('GO:0000011', 'Kinase activity', 0.9),
            make_embedding_item('GO:0000012', 'Transferase activity', 0.8),
            make_embedding_item('GO:0000013', 'Binding', 0.7),
        ]
        gene_scores = [
            make_gene_item('GO:0000011', 'Kinase activity', 0.0),
            make_gene_item('GO:0000012', 'Transferase activity', 0.95, matching_genes=['EGFR']),
            make_gene_item('GO:0000013', 'Binding', 0.0),
        ]

        ns_data = make_ns_data_for('go_mf')
        service = make_service()

        result = service._combine_go_scores_for(embedding_scores, gene_scores, ns_data)

        assert len(result) >= 2, "Expected at least 2 MF items above threshold"

        go_ids = [item['go_id'] for item in result]
        assert go_ids.index('GO:0000011') < go_ids.index('GO:0000012'), (
            f"GO:0000011 (text_sim=0.9) must rank above GO:0000012 (text_sim=0.8), "
            f"but got order: {go_ids}"
        )


# ============================================================================
# Test C — gene_overlap data still present on items
# ============================================================================

class TestGeneOverlapDataPreserved:
    """Test C: gene_overlap, matching_genes, and go_gene_count are present on items."""

    def test_c_gene_overlap_data_on_items(self):
        """
        gene_overlap value and matching_genes must be preserved on the output item
        for GO:0000002 which had non-zero gene_overlap input.

        This is required for the gene-overlap chip in Plan 29-05.
        Test does NOT check rank — only field presence.
        """
        embedding_scores = [
            make_embedding_item('GO:0000001', 'Process A', 0.9),
            make_embedding_item('GO:0000002', 'Process B', 0.8),
        ]
        gene_scores = [
            make_gene_item('GO:0000001', 'Process A', 0.0),
            make_gene_item('GO:0000002', 'Process B', 0.95,
                           matching_genes=['TP53', 'CASP3'], go_gene_count=25),
        ]

        ns_data = make_ns_data_for('go_bp')
        service = make_service()

        result = service._combine_go_scores_for(embedding_scores, gene_scores, ns_data)

        item_002 = next((r for r in result if r['go_id'] == 'GO:0000002'), None)
        assert item_002 is not None, "GO:0000002 must be in results"

        assert 'gene_overlap' in item_002, "gene_overlap field missing from result item"
        assert abs(item_002['gene_overlap'] - 0.95) < 1e-3, (
            f"gene_overlap should be ~0.95, got {item_002['gene_overlap']}"
        )
        assert 'matching_genes' in item_002, "matching_genes field missing from result item"
        assert 'TP53' in item_002['matching_genes'], "TP53 should be in matching_genes"
        assert 'go_gene_count' in item_002, "go_gene_count field missing from result item"
        assert item_002['go_gene_count'] == 25, f"go_gene_count should be 25, got {item_002['go_gene_count']}"


# ============================================================================
# Test D — gene-only signal does NOT promote past threshold
# ============================================================================

class TestGeneOnlySignalDoesNotPromote:
    """Test D: items with text_similarity=0.0 are excluded by min_threshold under v1.5."""

    def test_d_gene_only_excluded_by_threshold(self):
        """
        Under v1.5 weights (embedding=1.0, gene=0.0), an item with text_similarity=0.0
        and gene_overlap=0.95 gets hybrid_score=0.0 and is excluded by min_threshold
        (0.15 for go_bp, 0.12 for go_mf).
        """
        # Only in gene_scores, not in embedding_scores (or with 0 embedding score)
        embedding_scores = [
            make_embedding_item('GO:0000001', 'Process A', 0.9),
            # GO:0000002 has 0.0 text_similarity
            make_embedding_item('GO:0000002', 'Process B (gene only)', 0.0),
        ]
        gene_scores = [
            make_gene_item('GO:0000001', 'Process A', 0.0),
            make_gene_item('GO:0000002', 'Process B (gene only)', 0.95,
                           matching_genes=['BRCA1']),
        ]

        ns_data = make_ns_data_for('go_bp')
        service = make_service()

        result = service._combine_go_scores_for(embedding_scores, gene_scores, ns_data)

        go_ids = [item['go_id'] for item in result]
        assert 'GO:0000002' not in go_ids, (
            "GO:0000002 (text_similarity=0.0, gene_overlap=0.95) must be excluded "
            f"by min_threshold under v1.5 weights, but got items: {go_ids}"
        )
        assert 'GO:0000001' in go_ids, "GO:0000001 (text_similarity=0.9) must be present"


# ============================================================================
# Test E — IC boost still applies post-combine
# ============================================================================

class TestICBoostStillApplies:
    """Test E: _apply_ic_boost multiplies hybrid_score by (1 + ic_weight * IC_norm)."""

    def test_e_ic_boost_multiplier(self):
        """
        Given a suggestion with hybrid_score=0.8 and a hierarchy fixture where
        GO:0000001 has ic_score=0.5 and ic_weight=0.15, after _apply_ic_boost
        the hybrid_score must equal 0.8 * (1 + 0.15 * 0.5) = 0.8 * 1.075 = 0.86.

        Tests that _apply_ic_boost still operates on the v1.5 hybrid_score and
        has not been accidentally removed during the pure-semantic refactor.
        """
        # Tiny hierarchy fixture: ic_score and depth for GO:0000001
        hierarchy = {
            'GO:0000001': {
                'ic_score': 0.5,
                'depth': 3,
                'ancestors': set(),
            }
        }

        # Minimal config with ic_weight=0.15
        from src.core.config_loader import GoSuggestionConfig
        go_config = GoSuggestionConfig(
            hybrid_weights={'embedding': 1.0, 'gene': 0.0, 'multi_evidence_bonus': 0.0},
            hierarchy={'enabled': True, 'ic_weight': 0.15, 'redundancy_threshold': 0.20},
        )

        ns_data = _NamespaceData(
            embeddings={},
            name_embeddings={},
            metadata={},
            annotations={},
            hierarchy=hierarchy,
            config=go_config,
        )

        service = make_service()

        # Build a suggestion with known hybrid_score
        suggestions = [{
            'go_id': 'GO:0000001',
            'go_name': 'Test BP term',
            'hybrid_score': 0.8,
            'text_similarity': 0.8,
            'gene_overlap': 0.0,
            'match_types': ['text'],
        }]

        result = service._apply_ic_boost(suggestions, ns_data)

        assert len(result) == 1
        expected = round(min(0.8 * (1 + 0.15 * 0.5), 0.98), 4)  # 0.8 * 1.075 = 0.86
        assert abs(result[0]['hybrid_score'] - expected) < 1e-3, (
            f"Expected hybrid_score={expected} after IC boost, got {result[0]['hybrid_score']}"
        )
        assert result[0].get('depth') == 3, "depth should be attached by _apply_ic_boost"
