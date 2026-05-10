"""
Unit tests pinning the combine_scored_items() contract under v1.5 single-signal use.

These tests ensure:
  - Single-signal pure-semantic ranking works correctly with multi_evidence_bonus=0.0
  - No spurious bonus is applied when one signal has all-zero scores
  - Output fields (signal_scores, match_types, _signal_data, hybrid_score) are preserved
  - min_threshold filtering works correctly

Tests 1-4: combine_scored_items() behaviour (Task 1 — plan 29-01)
Tests 5-7: ConfigLoader v1.5 compatibility (Task 3 — plan 29-01)
"""
import pytest
from src.suggestions.scoring import combine_scored_items


# ============================================================================
# Fixtures
# ============================================================================

def make_items(scores, id_prefix="wp_", score_field="confidence_score"):
    """Create a list of scored items from a list of score values."""
    return [
        {
            "pathwayID": f"{id_prefix}{i}",
            "name": f"Pathway {i}",
            score_field: float(s),
        }
        for i, s in enumerate(scores)
    ]


# ============================================================================
# Task 1 Tests: combine_scored_items() v1.5 single-signal contract
# ============================================================================

class TestCombineScoredItemsSingleSignal:
    """Pin the combine_scored_items() contract for pure-semantic (single-signal) use."""

    def test_1_single_signal_ranking(self):
        """
        Test 1 (single-signal ranking): One signal, embedding weight=1.0,
        multi_evidence_bonus=0.0. Output is sorted by embedding score descending
        and hybrid_score equals min(score, max_score).
        """
        embedding_items = make_items([0.80, 0.50, 0.30])

        result = combine_scored_items(
            scored_lists={"embedding": embedding_items},
            id_field="pathwayID",
            weights={"embedding": 1.0},
            score_field_map={"embedding": "confidence_score"},
            multi_evidence_bonus=0.0,
            min_threshold=0.15,
            max_score=0.98,
        )

        assert len(result) == 3, f"Expected 3 items, got {len(result)}"

        # Sorted descending
        scores = [r["hybrid_score"] for r in result]
        assert scores == sorted(scores, reverse=True), "Results must be sorted descending"

        # hybrid_score == min(signal_score, max_score)
        for item in result:
            expected = round(min(item["signal_scores"]["embedding"], 0.98), 4)
            assert abs(item["hybrid_score"] - expected) < 1e-6, (
                f"hybrid_score mismatch: got {item['hybrid_score']}, expected {expected}"
            )

    def test_2_no_spurious_bonus_with_zero_signal(self):
        """
        Test 2 (no spurious bonus): Two signals where the second has all-zero scores.
        multi_evidence_bonus=0.0 must NOT bump any item. Also pins that active_signals
        considers score > 0.0, not key presence.
        """
        embedding_items = make_items([0.70, 0.40, 0.20])
        # Gene signal exists but all zeros (simulated by sending 0.0 scores)
        gene_items = make_items([0.0, 0.0, 0.0])

        result = combine_scored_items(
            scored_lists={"embedding": embedding_items, "gene": gene_items},
            id_field="pathwayID",
            weights={"embedding": 1.0, "gene": 0.0},
            score_field_map={
                "embedding": "confidence_score",
                "gene": "confidence_score",
            },
            multi_evidence_bonus=0.0,  # No bonus
            min_threshold=0.15,
            max_score=0.98,
        )

        assert len(result) == 3

        for item in result:
            # No bonus should be added — hybrid = embedding score only
            emb_score = item["signal_scores"]["embedding"]
            expected = round(min(emb_score, 0.98), 4)
            assert abs(item["hybrid_score"] - expected) < 1e-6, (
                f"Spurious bonus detected: hybrid_score={item['hybrid_score']} "
                f"but embedding only yields {expected}"
            )
            # Gene zero-signal should NOT appear in match_types
            assert "gene" not in item["match_types"], (
                "Zero-score gene signal must not appear in match_types"
            )

    def test_3_signal_scores_match_types_signal_data_preserved(self):
        """
        Test 3 (fields preserved): Output items expose signal_scores, match_types,
        _signal_data, and hybrid_score. v1.5 callers depend on these for chip
        rendering and per-signal data restore.
        """
        items = make_items([0.75, 0.50])

        result = combine_scored_items(
            scored_lists={"embedding": items},
            id_field="pathwayID",
            weights={"embedding": 1.0},
            score_field_map={"embedding": "confidence_score"},
            multi_evidence_bonus=0.0,
            min_threshold=0.10,
            max_score=0.98,
        )

        assert len(result) == 2

        for item in result:
            assert "signal_scores" in item, "signal_scores key missing"
            assert "match_types" in item, "match_types key missing"
            assert "_signal_data" in item, "_signal_data key missing"
            assert "hybrid_score" in item, "hybrid_score key missing"

            # signal_scores must contain the embedding key
            assert "embedding" in item["signal_scores"], "embedding missing from signal_scores"

            # match_types must contain 'embedding' since score > 0
            assert "embedding" in item["match_types"], "embedding missing from match_types"

            # _signal_data must contain the raw item under 'embedding' key
            assert "embedding" in item["_signal_data"], "embedding missing from _signal_data"
            assert "pathwayID" in item["_signal_data"]["embedding"], (
                "_signal_data['embedding'] must be the original item dict"
            )

    def test_4_min_threshold_respected(self):
        """
        Test 4 (min_threshold): Items below min_threshold are excluded.
        With embedding weight=1.0, an item with score 0.10 is excluded when
        min_threshold=0.15.
        """
        items = make_items([0.80, 0.50, 0.10])  # Last item below threshold

        result = combine_scored_items(
            scored_lists={"embedding": items},
            id_field="pathwayID",
            weights={"embedding": 1.0},
            score_field_map={"embedding": "confidence_score"},
            multi_evidence_bonus=0.0,
            min_threshold=0.15,
            max_score=0.98,
        )

        # Only 2 items should pass the threshold
        assert len(result) == 2, (
            f"Expected 2 items (above threshold), got {len(result)}"
        )

        # Confirm the excluded item (score=0.10) is not in the result
        result_ids = {item["pathwayID"] for item in result}
        assert "wp_2" not in result_ids, "Item with score 0.10 should be excluded by min_threshold"


# ============================================================================
# Task 3 Tests: ConfigLoader v1.5 compatibility
# ============================================================================

class TestConfigLoaderV15:
    """Pin ConfigLoader behaviour for v1.5 YAML (pure-semantic weights + ontology_post_combine_boost)."""

    def test_5_loader_parses_v15_scoring_config(self):
        """
        Test 5: ConfigLoader.get_default_config() or load_config() returns a config
        where pathway_suggestion.hybrid_weights.embedding == 1.0,
        hybrid_weights.gene == 0.0, and ontology_post_combine_boost.enabled is True
        with boost_weight == 0.15.
        """
        from src.core.config_loader import ConfigLoader

        cfg = ConfigLoader.load_config()

        assert cfg.pathway_suggestion.hybrid_weights.embedding == 1.0, (
            f"pathway_suggestion.hybrid_weights.embedding should be 1.0, "
            f"got {cfg.pathway_suggestion.hybrid_weights.embedding}"
        )
        assert cfg.pathway_suggestion.hybrid_weights.gene == 0.0, (
            f"pathway_suggestion.hybrid_weights.gene should be 0.0 (display-only chip), "
            f"got {cfg.pathway_suggestion.hybrid_weights.gene}"
        )
        assert cfg.pathway_suggestion.ontology_post_combine_boost.enabled is True, (
            "ontology_post_combine_boost.enabled should be True"
        )
        assert abs(cfg.pathway_suggestion.ontology_post_combine_boost.boost_weight - 0.15) < 1e-6, (
            f"ontology_post_combine_boost.boost_weight should be 0.15, "
            f"got {cfg.pathway_suggestion.ontology_post_combine_boost.boost_weight}"
        )

    def test_6_go_and_reactome_dict_weights_v15(self):
        """
        Test 6: GO and Reactome dict-shaped weights reflect v1.5 pure-semantic values.
        go_bp.hybrid_weights['embedding'] == 1.0, go_mf same, reactome_suggestion same.
        multi_evidence_bonus == 0.0 in all three.
        """
        from src.core.config_loader import ConfigLoader

        cfg = ConfigLoader.load_config()

        # go_bp
        assert cfg.go_bp.hybrid_weights["embedding"] == 1.0, (
            f"go_bp.hybrid_weights['embedding'] should be 1.0, got {cfg.go_bp.hybrid_weights['embedding']}"
        )
        assert cfg.go_bp.hybrid_weights["gene"] == 0.0, (
            f"go_bp.hybrid_weights['gene'] should be 0.0, got {cfg.go_bp.hybrid_weights['gene']}"
        )
        assert cfg.go_bp.hybrid_weights.get("multi_evidence_bonus", None) == 0.0, (
            f"go_bp multi_evidence_bonus should be 0.0"
        )

        # go_mf
        assert cfg.go_mf.hybrid_weights["embedding"] == 1.0, (
            f"go_mf.hybrid_weights['embedding'] should be 1.0, got {cfg.go_mf.hybrid_weights['embedding']}"
        )
        assert cfg.go_mf.hybrid_weights.get("multi_evidence_bonus", None) == 0.0, (
            f"go_mf multi_evidence_bonus should be 0.0"
        )

        # reactome
        assert cfg.reactome_suggestion.hybrid_weights["embedding"] == 1.0, (
            f"reactome_suggestion.hybrid_weights['embedding'] should be 1.0, "
            f"got {cfg.reactome_suggestion.hybrid_weights['embedding']}"
        )
        assert cfg.reactome_suggestion.hybrid_weights.get("multi_evidence_bonus", None) == 0.0, (
            f"reactome_suggestion multi_evidence_bonus should be 0.0"
        )

    def test_7_loader_tolerant_of_missing_ontology_post_combine_boost(self, tmp_path):
        """
        Test 7 (no schema break under prior YAML): If ontology_post_combine_boost is
        missing from the YAML (v1.4-shaped fixture), loader still returns a config
        with sensible defaults and does NOT raise.
        """
        import yaml
        from src.core.config_loader import ConfigLoader

        # Minimal v1.4-shaped pathway_suggestion (no ontology_post_combine_boost)
        minimal_yaml = {
            "pathway_suggestion": {
                "hybrid_weights": {
                    "gene": 0.35,
                    "text": 0.0,
                    "embedding": 0.50,
                    "ontology": 0.15,
                    "multi_evidence_bonus": 0.05,
                },
                "gene_scoring": {
                    "overlap_weight": 0.4,
                    "specificity_weight": 0.4,
                    "specificity_scaling_factor": 10.0,
                    "base_boost": 0.15,
                    "min_genes_for_high_confidence": 3,
                    "low_gene_penalty": 0.8,
                    "max_confidence": 0.95,
                },
                "confidence_scoring": {
                    "min_confidence": 0.08,
                    "max_confidence": 0.98,
                },
            },
            "ke_go_assessment": {
                "dimension_weights": {
                    "connection": 0.33,
                    "specificity": 0.33,
                    "evidence": 0.34,
                },
            },
            "metadata": {"version": "1.4.0"},
        }

        yaml_path = tmp_path / "test_v14_scoring_config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(minimal_yaml, f)

        # Should NOT raise — fallback to defaults for missing fields
        cfg = ConfigLoader.load_config(config_path=str(yaml_path))

        # ontology_post_combine_boost should use defaults (enabled=True, boost_weight=0.15)
        assert cfg.pathway_suggestion.ontology_post_combine_boost.enabled is True, (
            "Default ontology_post_combine_boost.enabled should be True when key absent from YAML"
        )
        assert abs(cfg.pathway_suggestion.ontology_post_combine_boost.boost_weight - 0.15) < 1e-6, (
            "Default ontology_post_combine_boost.boost_weight should be 0.15 when key absent from YAML"
        )
