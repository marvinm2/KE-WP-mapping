"""
Configuration Loader for Scoring Parameters

This module provides a singleton configuration loader that reads scoring
parameters from a YAML file and validates them. It supports graceful
fallback to default values matching the original hardcoded constants.

Usage:
    from config_loader import ConfigLoader

    # Load config
    config = ConfigLoader.load_config()

    # Access values
    overlap_weight = config.pathway_suggestion.gene_scoring.overlap_weight

Author: KE-WP Mapping Team
Date: 2026-01-12
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import yaml
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class GeneScoring:
    """Gene-based pathway suggestion scoring parameters with pathway specificity"""
    overlap_weight: float = 0.4
    specificity_weight: float = 0.4
    specificity_scaling_factor: float = 10.0
    base_boost: float = 0.15
    min_genes_for_high_confidence: int = 3
    low_gene_penalty: float = 0.8
    max_confidence: float = 0.95


@dataclass
class AlgorithmWeights:
    """Text similarity algorithm weights"""
    jaccard: float = 0.0
    sequence: float = 0.0
    substring: float = 0.0
    threshold: float = 0.0


@dataclass
class TextSimilarity:
    """Text similarity scoring parameters"""
    important_bio_terms_weight: float = 2.0

    # Adaptive weighting based on overlap quality
    high_overlap_weights: Dict[str, float] = field(default_factory=lambda: {
        'jaccard': 0.65, 'sequence': 0.25, 'substring': 0.10, 'threshold': 0.7
    })
    medium_overlap_weights: Dict[str, float] = field(default_factory=lambda: {
        'jaccard': 0.50, 'sequence': 0.30, 'substring': 0.20, 'threshold': 0.4
    })
    good_substring_weights: Dict[str, float] = field(default_factory=lambda: {
        'substring': 0.60, 'jaccard': 0.25, 'sequence': 0.15, 'threshold': 0.6
    })
    high_sequence_weights: Dict[str, float] = field(default_factory=lambda: {
        'sequence': 0.55, 'jaccard': 0.30, 'substring': 0.15, 'threshold': 0.7
    })
    low_quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'sequence': 0.35, 'jaccard': 0.35, 'substring': 0.30, 'penalty': 0.85
    })

    # Boost parameters
    synonym_boost: float = 0.30
    domain_boost: float = 0.25
    boost_threshold: float = 0.6
    high_score_boost_factor: float = 1.15
    low_score_boost_factor: float = 1.25
    boost_contribution: float = 0.2


@dataclass
class ConfidenceTier:
    """Confidence scoring tier parameters"""
    threshold: float = 0.0
    base: float = 0.0
    multiplier: float = 0.0


@dataclass
class TitleBoost:
    """Title similarity boost parameters"""
    threshold: float = 0.0
    boost: float = 0.0


@dataclass
class ConfidenceScoring:
    """Confidence score calculation parameters"""
    # Non-linear scaling tiers
    tier_high: Dict[str, float] = field(default_factory=lambda: {
        'threshold': 0.8, 'base': 0.48, 'multiplier': 0.6
    })
    tier_medium: Dict[str, float] = field(default_factory=lambda: {
        'threshold': 0.6, 'base': 0.36, 'multiplier': 0.6
    })
    tier_low: Dict[str, float] = field(default_factory=lambda: {
        'threshold': 0.4, 'base': 0.24, 'multiplier': 0.6
    })
    tier_minimum: Dict[str, float] = field(default_factory=lambda: {
        'multiplier': 0.6
    })

    # Title similarity boosts
    title_boosts: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'very_high': {'threshold': 0.8, 'boost': 0.15},
        'high': {'threshold': 0.6, 'boost': 0.10},
        'medium': {'threshold': 0.4, 'boost': 0.05}
    })

    # Consistency bonus
    consistency: Dict[str, float] = field(default_factory=lambda: {
        'threshold': 0.1, 'min_score': 0.5, 'boost': 0.10
    })

    # Penalties
    low_title_penalty: Dict[str, float] = field(default_factory=lambda: {
        'title_threshold': 0.2, 'desc_threshold': 0.5, 'multiplier': 0.8
    })

    # Biological level adjustments
    biological_level: Dict[str, float] = field(default_factory=lambda: {
        'molecular_boost': 0.10,
        'molecular_title_threshold': 0.7,
        'higher_level_boost': 0.05
    })

    # Length bonuses
    length_bonuses: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'very_descriptive': {'word_threshold': 5, 'boost': 0.08},
        'moderately_descriptive': {'word_threshold': 3, 'boost': 0.05},
        'minimally_descriptive': {'word_threshold': 2, 'boost': 0.02}
    })

    # Length penalties
    length_penalties: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'very_different': {'diff_threshold': 4, 'multiplier': 0.95},
        'somewhat_different': {'diff_threshold': 2, 'multiplier': 0.98}
    })

    # Similarity adjustments
    similarity_adjustments: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'excellent': {'threshold': 0.9, 'boost': 0.05},
        'very_good': {'threshold': 0.8, 'boost': 0.03},
        'poor': {'threshold': 0.4, 'multiplier': 0.9}
    })

    # Tie-breaking
    random_component_max: float = 0.01

    # Final bounds
    min_confidence: float = 0.08
    max_confidence: float = 0.98

    # Quality tier thresholds for UI badges
    quality_tiers: Dict[str, float] = field(default_factory=lambda: {
        'excellent_threshold': 0.70,
        'good_threshold': 0.50,
        'moderate_threshold': 0.30
    })


@dataclass
class DynamicThresholds:
    """Dynamic threshold calculation parameters"""
    base_threshold: float = 0.30

    high_specificity_terms: Dict[str, Any] = field(default_factory=lambda: {
        'adjustment': 0.05,
        'terms': [
            'apoptosis', 'proliferation', 'differentiation', 'inflammation',
            'oxidative', 'dna damage', 'cell death', 'receptor', 'enzyme',
            'kinase', 'phosphatase'
        ]
    })

    broad_process_terms: Dict[str, Any] = field(default_factory=lambda: {
        'adjustment': -0.05,
        'terms': [
            'function', 'dysfunction', 'activity', 'regulation', 'response',
            'stress', 'development', 'growth', 'metabolism', 'transport'
        ]
    })

    biological_level_adjustments: Dict[str, float] = field(default_factory=lambda: {
        'molecular': -0.03,
        'cellular': 0.0,
        'tissue': -0.08,
        'organ': -0.08
    })


@dataclass
class BiologicalLevelMultipliers:
    """Biological level scoring multipliers"""
    molecular: Dict[str, float] = field(default_factory=lambda: {
        'pathway_name_match': 1.3,
        'gene_protein_match': 1.2
    })
    cellular: Dict[str, float] = field(default_factory=lambda: {
        'cellular_process_match': 1.2,
        'good_pathway_match': 1.1,
        'good_pathway_threshold': 0.5
    })
    tissue_organ: Dict[str, float] = field(default_factory=lambda: {
        'system_level_match': 1.3,
        'disease_pathway_match': 1.2
    })


@dataclass
class SubstringScoring:
    """Substring matching scoring parameters"""
    exact_match: Dict[str, float] = field(default_factory=lambda: {
        'base_score': 0.6,
        'length_bonus': 0.3
    })
    common_words: Dict[str, Any] = field(default_factory=lambda: {
        'long_word_length': 5,
        'medium_word_length': 3,
        'long_weight': 1.0,
        'bio_term_weight': 0.8,
        'medium_weight': 0.6
    })
    weighted_ratio: Dict[str, float] = field(default_factory=lambda: {
        'multiplier': 0.7,
        'power': 0.8,
        'max_score': 0.55
    })


@dataclass
class ScoreTransformation:
    """BioBERT score transformation configuration"""
    method: str = "power"           # Options: power, linear, none
    power_exponent: float = 2.5     # For power method: score^exponent
    scale_factor: float = 0.75      # For linear method: score × factor
    output_min: float = 0.0         # Floor for transformed scores
    output_max: float = 0.70        # Ceiling for transformed scores


@dataclass
class EntityExtraction:
    """Entity extraction configuration for more specific matching"""
    enabled: bool = True            # Extract entities before embedding
    min_entity_length: int = 3      # Minimum characters for an entity
    include_numbers: bool = True    # Include alphanumeric terms (CYP2E1, IL6)
    biological_terms_only: bool = False  # Filter to known bio terms only


@dataclass
class EmbeddingBasedMatching:
    """BioBERT embedding-based matching configuration"""
    enabled: bool = False
    model: str = "dmis-lab/biobert-base-cased-v1.2"
    min_threshold: float = 0.4      # Minimum similarity to include
    use_gpu: bool = True
    precomputed_embeddings: str = "pathway_embeddings.npy"
    precomputed_ke_embeddings: str = "ke_embeddings.npy"
    fallback_to_text: bool = True
    title_weight: float = 0.85      # Weight for title similarity (description = 1 - this)
    skip_precomputed_for_titles: bool = True  # Skip pre-computed for entity extraction
    entity_extraction: EntityExtraction = field(default_factory=EntityExtraction)
    score_transformation: ScoreTransformation = field(default_factory=ScoreTransformation)


@dataclass
class HybridWeights:
    """Hybrid scoring weights for multi-signal combination"""
    gene: float = 0.35
    text: float = 0.35
    embedding: float = 0.30
    multi_evidence_bonus: float = 0.05


@dataclass
class PathwaySuggestionConfig:
    """Pathway suggestion scoring configuration"""
    gene_scoring: GeneScoring = field(default_factory=GeneScoring)
    text_similarity: TextSimilarity = field(default_factory=TextSimilarity)
    confidence_scoring: ConfidenceScoring = field(default_factory=ConfidenceScoring)
    dynamic_thresholds: DynamicThresholds = field(default_factory=DynamicThresholds)
    biological_level_multipliers: BiologicalLevelMultipliers = field(default_factory=BiologicalLevelMultipliers)
    substring_scoring: SubstringScoring = field(default_factory=SubstringScoring)
    embedding_based_matching: EmbeddingBasedMatching = field(default_factory=EmbeddingBasedMatching)
    hybrid_weights: HybridWeights = field(default_factory=HybridWeights)


@dataclass
class GoSuggestionConfig:
    """GO term suggestion scoring configuration"""
    hybrid_weights: Dict[str, float] = field(default_factory=lambda: {
        'embedding': 0.55,
        'gene': 0.45,
        'multi_evidence_bonus': 0.05
    })
    min_threshold: float = 0.15
    embedding_min_threshold: float = 0.3
    gene_min_threshold: float = 0.05
    gene_min_term_size: int = 10


@dataclass
class KEGoAssessmentConfig:
    """KE-GO assessment scoring configuration"""
    term_specificity: Dict[str, int] = field(default_factory=lambda: {
        'exact': 3,
        'parent_child': 2,
        'related': 1,
        'broad': 0
    })

    evidence_support: Dict[str, int] = field(default_factory=lambda: {
        'experimental': 3,
        'curated': 2,
        'inferred': 1,
        'assumed': 0
    })

    gene_overlap: Dict[str, float] = field(default_factory=lambda: {
        'high_threshold': 0.5,
        'high_score': 2,
        'moderate_threshold': 0.2,
        'moderate_score': 1,
        'low_score': 0
    })

    bio_level_bonus: Dict[str, float] = field(default_factory=lambda: {
        'molecular_process': 1.0,
        'cellular_process': 1.0,
        'general_process': 0.5
    })

    confidence_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'high': 6,
        'medium': 3
    })

    max_scores: Dict[str, float] = field(default_factory=lambda: {
        'with_bio_bonus': 9.0,
        'without_bio_bonus': 8.0
    })

    connection_types: List[str] = field(default_factory=lambda: [
        'describes', 'involves', 'related', 'context'
    ])


@dataclass
class KEPathwayAssessmentConfig:
    """KE-Pathway assessment scoring configuration"""
    evidence_quality: Dict[str, int] = field(default_factory=lambda: {
        'known': 3,
        'likely': 2,
        'possible': 1,
        'uncertain': 0
    })

    pathway_specificity: Dict[str, int] = field(default_factory=lambda: {
        'specific': 2,
        'includes': 1,
        'loose': 0
    })

    ke_coverage: Dict[str, float] = field(default_factory=lambda: {
        'complete': 1.5,
        'keysteps': 1.0,
        'minor': 0.5
    })

    biological_level: Dict[str, Any] = field(default_factory=lambda: {
        'bonus': 1.0,
        'qualifying_levels': ['molecular', 'cellular', 'tissue']
    })

    confidence_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'high': 5.0,
        'medium': 2.5
    })

    max_scores: Dict[str, float] = field(default_factory=lambda: {
        'with_bio_bonus': 7.5,
        'without_bio_bonus': 6.5
    })

    connection_types: List[str] = field(default_factory=lambda: [
        'causative', 'responsive', 'bidirectional', 'unclear'
    ])


@dataclass
class ScoringConfig:
    """Complete scoring configuration"""
    pathway_suggestion: PathwaySuggestionConfig = field(default_factory=PathwaySuggestionConfig)
    ke_pathway_assessment: KEPathwayAssessmentConfig = field(default_factory=KEPathwayAssessmentConfig)
    go_suggestion: GoSuggestionConfig = field(default_factory=GoSuggestionConfig)
    ke_go_assessment: KEGoAssessmentConfig = field(default_factory=KEGoAssessmentConfig)
    metadata: Dict[str, str] = field(default_factory=lambda: {
        'version': '1.0.0',
        'last_modified': '2026-01-12',
        'description': 'Scoring configuration for KE-WP Mapping'
    })


# =============================================================================
# Configuration Loader
# =============================================================================

class ConfigLoader:
    """
    Singleton configuration loader for scoring parameters.

    Provides methods to load configuration from YAML file with validation
    and graceful fallback to default values.
    """

    _instance = None
    _config_cache = None
    _config_file_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> ScoringConfig:
        """
        Load scoring configuration from YAML file.

        Args:
            config_path: Path to YAML config file (default: scoring_config.yaml)

        Returns:
            ScoringConfig object with validated parameters

        Raises:
            ValueError: If config validation fails
        """
        if config_path is None:
            # Default path in project root
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'scoring_config.yaml'
            )

        try:
            # Check if file exists
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return cls.get_default_config()

            # Load YAML
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)

            if not config_dict:
                logger.warning(f"Empty config file at {config_path}, using defaults")
                return cls.get_default_config()

            # Build config object
            config = cls._build_config_from_dict(config_dict)

            # Validate
            cls._validate_config(config)

            logger.info(f"Successfully loaded scoring configuration from {config_path}")
            cls._config_cache = config
            cls._config_file_path = config_path

            return config

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            logger.info("Falling back to default configuration")
            return cls.get_default_config()

    @classmethod
    def get_default_config(cls) -> ScoringConfig:
        """
        Get default configuration matching original hardcoded values.

        Returns:
            ScoringConfig with default values
        """
        logger.info("Using default scoring configuration")
        return ScoringConfig()

    @classmethod
    def _build_config_from_dict(cls, config_dict: Dict) -> ScoringConfig:
        """Build ScoringConfig from dictionary"""
        try:
            # Extract sections
            pathway_dict = config_dict.get('pathway_suggestion', {})
            ke_pathway_dict = config_dict.get('ke_pathway_assessment', {})
            go_suggestion_dict = config_dict.get('go_suggestion', {})
            ke_go_dict = config_dict.get('ke_go_assessment', {})
            metadata_dict = config_dict.get('metadata', {})

            # Build pathway suggestion config
            gene_scoring = GeneScoring(**pathway_dict.get('gene_scoring', {}))
            text_similarity = TextSimilarity(**pathway_dict.get('text_similarity', {}))
            confidence_scoring = ConfidenceScoring(**pathway_dict.get('confidence_scoring', {}))
            dynamic_thresholds = DynamicThresholds(**pathway_dict.get('dynamic_thresholds', {}))
            bio_level_mult = BiologicalLevelMultipliers(**pathway_dict.get('biological_level_multipliers', {}))
            substring_scoring = SubstringScoring(**pathway_dict.get('substring_scoring', {}))

            # Handle nested configs in embedding_based_matching
            embedding_dict = pathway_dict.get('embedding_based_matching', {}).copy()

            # Extract and build nested score_transformation
            score_transform_dict = embedding_dict.pop('score_transformation', {})
            score_transformation = ScoreTransformation(**score_transform_dict)

            # Extract and build nested entity_extraction
            entity_extract_dict = embedding_dict.pop('entity_extraction', {})
            entity_extraction = EntityExtraction(**entity_extract_dict)

            embedding_matching = EmbeddingBasedMatching(
                **embedding_dict,
                score_transformation=score_transformation,
                entity_extraction=entity_extraction
            )

            hybrid_weights = HybridWeights(**pathway_dict.get('hybrid_weights', {}))

            pathway_config = PathwaySuggestionConfig(
                gene_scoring=gene_scoring,
                text_similarity=text_similarity,
                confidence_scoring=confidence_scoring,
                dynamic_thresholds=dynamic_thresholds,
                biological_level_multipliers=bio_level_mult,
                substring_scoring=substring_scoring,
                embedding_based_matching=embedding_matching,
                hybrid_weights=hybrid_weights
            )

            # Build KE-pathway assessment config
            ke_pathway_config = KEPathwayAssessmentConfig(**ke_pathway_dict)

            # Build GO suggestion config
            go_suggestion_config = GoSuggestionConfig(**go_suggestion_dict)

            # Build KE-GO assessment config
            ke_go_config = KEGoAssessmentConfig(**ke_go_dict)

            return ScoringConfig(
                pathway_suggestion=pathway_config,
                ke_pathway_assessment=ke_pathway_config,
                go_suggestion=go_suggestion_config,
                ke_go_assessment=ke_go_config,
                metadata=metadata_dict
            )

        except Exception as e:
            logger.error(f"Error building config from dictionary: {e}")
            raise ValueError(f"Invalid configuration structure: {e}")

    @classmethod
    def _validate_config(cls, config: ScoringConfig):
        """
        Validate configuration values.

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate gene scoring
        gs = config.pathway_suggestion.gene_scoring
        if not 0 <= gs.overlap_weight <= 1:
            errors.append(f"gene_scoring.overlap_weight ({gs.overlap_weight}) must be between 0 and 1")
        if not 0 <= gs.specificity_weight <= 1:
            errors.append(f"gene_scoring.specificity_weight ({gs.specificity_weight}) must be between 0 and 1")
        if not 1 <= gs.specificity_scaling_factor <= 20:
            errors.append(f"gene_scoring.specificity_scaling_factor ({gs.specificity_scaling_factor}) must be between 1 and 20")
        if not 0 <= gs.base_boost <= 0.3:
            errors.append(f"gene_scoring.base_boost ({gs.base_boost}) must be between 0 and 0.3")
        if not 2 <= gs.min_genes_for_high_confidence <= 5:
            errors.append(f"gene_scoring.min_genes_for_high_confidence ({gs.min_genes_for_high_confidence}) must be between 2 and 5")
        if not 0.5 <= gs.low_gene_penalty <= 1:
            errors.append(f"gene_scoring.low_gene_penalty ({gs.low_gene_penalty}) must be between 0.5 and 1")
        if not 0.8 <= gs.max_confidence <= 1:
            errors.append(f"gene_scoring.max_confidence ({gs.max_confidence}) must be between 0.8 and 1")

        # Validate confidence bounds
        cs = config.pathway_suggestion.confidence_scoring
        if not 0 <= cs.min_confidence <= 1:
            errors.append(f"min_confidence ({cs.min_confidence}) must be between 0 and 1")
        if not 0 <= cs.max_confidence <= 1:
            errors.append(f"max_confidence ({cs.max_confidence}) must be between 0 and 1")
        if cs.min_confidence >= cs.max_confidence:
            errors.append(f"min_confidence must be less than max_confidence")

        # Validate KE-pathway thresholds
        ke = config.ke_pathway_assessment
        if ke.confidence_thresholds['high'] <= ke.confidence_thresholds['medium']:
            errors.append("High confidence threshold must be greater than medium threshold")

        # Validate evidence quality scores
        if not all(isinstance(v, int) and v >= 0 for v in ke.evidence_quality.values()):
            errors.append("Evidence quality scores must be non-negative integers")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        logger.debug("Configuration validation passed")

    @classmethod
    def reload_config(cls) -> ScoringConfig:
        """
        Reload configuration from last loaded file path.

        Returns:
            Reloaded ScoringConfig
        """
        if cls._config_file_path:
            logger.info(f"Reloading configuration from {cls._config_file_path}")
            return cls.load_config(cls._config_file_path)
        else:
            logger.warning("No previous config file path, returning cached or default config")
            return cls._config_cache or cls.get_default_config()

    @classmethod
    def export_config_to_dict(cls, config: ScoringConfig) -> Dict:
        """
        Export configuration to dictionary format.

        Args:
            config: ScoringConfig object

        Returns:
            Dictionary representation suitable for YAML export
        """
        return asdict(config)


# =============================================================================
# Helper Functions
# =============================================================================

def get_config() -> ScoringConfig:
    """
    Convenience function to get scoring configuration.

    Returns:
        ScoringConfig object
    """
    loader = ConfigLoader()
    if loader._config_cache:
        return loader._config_cache
    return ConfigLoader.load_config()


if __name__ == '__main__':
    # Test config loading
    logging.basicConfig(level=logging.INFO)

    print("Testing ConfigLoader...")
    print("=" * 60)

    # Test default config
    print("\n1. Loading default configuration...")
    default_config = ConfigLoader.get_default_config()
    print(f"   Gene scoring overlap_weight: {default_config.pathway_suggestion.gene_scoring.overlap_weight}")
    print(f"   Gene scoring specificity_weight: {default_config.pathway_suggestion.gene_scoring.specificity_weight}")
    print(f"   Evidence quality 'known': {default_config.ke_pathway_assessment.evidence_quality['known']}")
    print(f"   Confidence high threshold: {default_config.ke_pathway_assessment.confidence_thresholds['high']}")

    # Test file loading (will fall back to defaults if file doesn't exist)
    print("\n2. Attempting to load from file...")
    file_config = ConfigLoader.load_config()
    print(f"   Gene scoring overlap_weight: {file_config.pathway_suggestion.gene_scoring.overlap_weight}")
    print(f"   Gene scoring specificity_weight: {file_config.pathway_suggestion.gene_scoring.specificity_weight}")
    print(f"   Config version: {file_config.metadata.get('version', 'unknown')}")

    print("\n" + "=" * 60)
    print("ConfigLoader test complete!")
