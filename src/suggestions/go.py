"""
GO Term Suggestion Service
Provides intelligent GO Biological Process term suggestions for Key Events
using pre-computed embeddings and gene annotation overlap.
"""
import json
import logging
import os
from typing import Dict, List

import numpy as np
from src.core.config_loader import ConfigLoader
from src.suggestions.ke_genes import get_genes_from_ke
from src.suggestions.scoring import combine_scored_items
from src.utils.text import remove_directionality_terms

logger = logging.getLogger(__name__)


class GoSuggestionService:
    """Service for generating GO BP term suggestions based on Key Events"""

    def __init__(
        self,
        cache_model=None,
        config=None,
        embedding_service=None,
        go_embeddings_path='data/go_bp_embeddings.npy',
        go_name_embeddings_path='data/go_bp_name_embeddings.npy',
        go_metadata_path='data/go_bp_metadata.json',
        go_annotations_path='data/go_bp_gene_annotations.json'
    ):
        self.cache_model = cache_model
        self.config = config or ConfigLoader.get_default_config()
        self.embedding_service = embedding_service
        self.aop_wiki_endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"

        # Load pre-computed GO data
        self.go_embeddings = {}
        self.go_name_embeddings = {}
        self.go_metadata = {}
        self.go_gene_annotations = {}

        self._load_go_embeddings(go_embeddings_path)
        self._load_go_name_embeddings(go_name_embeddings_path)
        self._load_go_metadata(go_metadata_path)
        self._load_go_annotations(go_annotations_path)

    def _load_go_embeddings(self, path):
        """Load pre-computed GO BP embeddings"""
        if os.path.exists(path):
            try:
                self.go_embeddings = np.load(path, allow_pickle=True).item()
                logger.info("Loaded %d GO BP embeddings", len(self.go_embeddings))
            except Exception as e:
                logger.warning("Could not load GO embeddings: %s", e)
        else:
            logger.warning("GO embeddings file not found: %s", path)

    def _load_go_name_embeddings(self, path):
        """Load pre-computed GO BP name-only embeddings"""
        if os.path.exists(path):
            try:
                self.go_name_embeddings = np.load(path, allow_pickle=True).item()
                logger.info("Loaded %d GO BP name embeddings", len(self.go_name_embeddings))
            except Exception as e:
                logger.warning("Could not load GO name embeddings: %s", e)
        else:
            logger.warning("GO name embeddings file not found: %s, will use combined only", path)

    def _load_go_metadata(self, path):
        """Load GO BP metadata (names, definitions, relationships)"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.go_metadata = json.load(f)
                logger.info("Loaded metadata for %d GO BP terms", len(self.go_metadata))
            except Exception as e:
                logger.warning("Could not load GO metadata: %s", e)
        else:
            logger.warning("GO metadata file not found: %s", path)

    def _load_go_annotations(self, path):
        """Load GO BP gene annotations"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.go_gene_annotations = json.load(f)
                logger.info("Loaded gene annotations for %d GO BP terms", len(self.go_gene_annotations))
            except Exception as e:
                logger.warning("Could not load GO annotations: %s", e)
        else:
            logger.warning("GO annotations file not found: %s", path)

    def get_go_suggestions(
        self,
        ke_id: str,
        ke_title: str,
        limit: int = 20,
        method_filter: str = 'all'
    ) -> Dict:
        """
        Get GO BP term suggestions for a Key Event

        Args:
            ke_id: Key Event ID (e.g., "KE 55")
            ke_title: Key Event title for text-based matching
            limit: Maximum number of suggestions to return
            method_filter: 'all', 'text', or 'gene'

        Returns:
            Dictionary containing suggestions with scores
        """
        try:
            logger.info("Getting GO suggestions for %s (filter: %s)", ke_id, method_filter)

            # Get genes associated with this KE
            genes = self._get_genes_from_ke(ke_id)

            # Compute embedding-based scores
            embedding_scores = []
            if method_filter in ('all', 'text') and self.embedding_service and self.go_embeddings:
                embedding_scores = self._compute_embedding_scores(ke_id, ke_title)

            # Compute gene-based scores
            gene_scores = []
            if method_filter in ('all', 'gene') and genes and self.go_gene_annotations:
                gene_scores = self._compute_gene_overlap_scores(genes)

            # Combine scores
            if method_filter == 'all':
                combined = self._combine_go_scores(embedding_scores, gene_scores)
            elif method_filter == 'text':
                combined = embedding_scores
            elif method_filter == 'gene':
                combined = gene_scores
            else:
                combined = self._combine_go_scores(embedding_scores, gene_scores)

            # Sort by score and limit
            combined.sort(key=lambda x: x['hybrid_score'], reverse=True)
            limited = combined[:limit]

            return {
                "ke_id": ke_id,
                "ke_title": ke_title,
                "genes_found": len(genes),
                "gene_list": genes,
                "suggestions": limited,
                "total_suggestions": len(combined),
                "method_filter": method_filter,
                "embedding_count": len(embedding_scores),
                "gene_count": len(gene_scores)
            }

        except Exception as e:
            logger.error("Error getting GO suggestions for %s: %s", ke_id, e)
            return {
                "error": "Failed to generate GO suggestions",
                "ke_id": ke_id,
                "ke_title": ke_title,
            }

    def _get_genes_from_ke(self, ke_id: str) -> List[str]:
        """Extract HGNC gene symbols associated with a Key Event"""
        return get_genes_from_ke(ke_id, self.aop_wiki_endpoint, self.cache_model)

    def _compute_embedding_scores(self, ke_id: str, ke_title: str) -> List[Dict]:
        """
        Compute embedding-based similarity between KE and all GO BP terms.

        Uses split name/definition embeddings weighted like pathway title/description
        (default 85% name, 15% definition). Falls back to combined-only if name
        embeddings are not available.
        """
        if not self.embedding_service or not self.go_embeddings:
            return []

        try:
            # Clean KE title
            ke_title_clean = remove_directionality_terms(ke_title)

            # Get KE embedding
            ke_emb = self.embedding_service.get_ke_embedding(ke_id, ke_title_clean)

            # Get GO config thresholds
            go_config = getattr(self.config, 'go_suggestion', None)
            min_threshold = getattr(go_config, 'embedding_min_threshold', 0.3) if go_config else 0.3

            # Get GO-specific name/definition weighting
            name_weight = getattr(go_config, 'name_weight', 0.60) if go_config else 0.60
            def_weight = 1.0 - name_weight

            ke_norm = np.linalg.norm(ke_emb)

            # Use split name + definition embeddings if available
            if self.go_name_embeddings:
                # Use intersection of IDs present in both embedding sets
                go_ids = [gid for gid in self.go_embeddings.keys()
                          if gid in self.go_name_embeddings]

                name_emb_array = np.array([self.go_name_embeddings[gid] for gid in go_ids])
                def_emb_array = np.array([self.go_embeddings[gid] for gid in go_ids])

                # Vectorized cosine similarities
                raw_name_sim = np.dot(name_emb_array, ke_emb) / (
                    np.linalg.norm(name_emb_array, axis=1) * ke_norm + 1e-8)
                raw_def_sim = np.dot(def_emb_array, ke_emb) / (
                    np.linalg.norm(def_emb_array, axis=1) * ke_norm + 1e-8)

                # Transform both independently
                transformed_name = self.embedding_service._transform_similarity_batch(raw_name_sim)
                transformed_def = self.embedding_service._transform_similarity_batch(raw_def_sim)

                # Weighted combination
                combined = (transformed_name * name_weight) + (transformed_def * def_weight)

                logger.info("Split embedding scoring: %.0f%% name + %.0f%% definition", name_weight * 100, def_weight * 100)
            else:
                # Fallback: combined-only embeddings
                go_ids = list(self.go_embeddings.keys())
                go_emb_array = np.array([self.go_embeddings[gid] for gid in go_ids])
                go_norms = np.linalg.norm(go_emb_array, axis=1)
                raw_similarities = np.dot(go_emb_array, ke_emb) / (go_norms * ke_norm + 1e-8)
                combined = self.embedding_service._transform_similarity_batch(raw_similarities)
                transformed_name = None
                transformed_def = None

            # Filter and build results
            results = []
            for i, go_id in enumerate(go_ids):
                score = float(combined[i])
                if score < min_threshold:
                    continue

                metadata = self.go_metadata.get(go_id, {})
                result = {
                    'go_id': go_id,
                    'go_name': metadata.get('name', 'Unknown'),
                    'go_definition': metadata.get('definition', ''),
                    'synonyms': metadata.get('synonyms', []),
                    'text_similarity': score,
                    'gene_overlap': 0.0,
                    'matching_genes': [],
                    'hybrid_score': score,
                    'match_types': ['text'],
                    'quickgo_link': f"https://www.ebi.ac.uk/QuickGO/term/{go_id}",
                    'go_gene_count': len(self.go_gene_annotations.get(go_id, []))
                }

                # Add split scores if available
                if transformed_name is not None:
                    result['name_similarity'] = round(float(transformed_name[i]), 4)
                    result['definition_similarity'] = round(float(transformed_def[i]), 4)

                results.append(result)

            logger.info("Found %d embedding-based GO suggestions", len(results))
            return results

        except Exception as e:
            logger.error("Embedding-based GO suggestion failed: %s", e)
            return []

    def _compute_gene_overlap_scores(self, ke_genes: List[str]) -> List[Dict]:
        """
        Compute gene overlap between KE genes and GO term gene annotations.

        Uses weighted KE overlap + Jaccard similarity with dampening for small terms.
        """
        if not ke_genes or not self.go_gene_annotations:
            return []

        try:
            go_config = getattr(self.config, 'go_suggestion', None)
            min_threshold = getattr(go_config, 'gene_min_threshold', 0.05) if go_config else 0.05
            min_term_size = getattr(go_config, 'gene_min_term_size', 10) if go_config else 10

            ke_gene_set = set(ke_genes)
            results = []

            for go_id, go_genes in self.go_gene_annotations.items():
                go_gene_set = set(go_genes)

                # Compute overlap
                matching = ke_gene_set.intersection(go_gene_set)
                if not matching:
                    continue

                # Jaccard similarity
                union = ke_gene_set.union(go_gene_set)
                jaccard = len(matching) / len(union) if union else 0.0

                # Overlap ratio from KE perspective
                ke_overlap = len(matching) / len(ke_gene_set) if ke_gene_set else 0.0

                # Combined gene score (weighted: KE overlap matters more)
                gene_score = (ke_overlap * 0.7) + (jaccard * 0.3)

                # Dampen small GO terms to avoid inflation
                go_size = len(go_gene_set)
                if go_size < min_term_size:
                    size_factor = go_size / min_term_size
                    gene_score *= size_factor

                if gene_score < min_threshold:
                    continue

                metadata = self.go_metadata.get(go_id, {})
                results.append({
                    'go_id': go_id,
                    'go_name': metadata.get('name', 'Unknown'),
                    'go_definition': metadata.get('definition', ''),
                    'synonyms': metadata.get('synonyms', []),
                    'text_similarity': 0.0,
                    'gene_overlap': round(gene_score, 4),
                    'matching_genes': sorted(list(matching)),
                    'hybrid_score': gene_score,
                    'match_types': ['gene'],
                    'quickgo_link': f"https://www.ebi.ac.uk/QuickGO/term/{go_id}",
                    'go_gene_count': go_size
                })

            logger.info("Found %d gene-based GO suggestions", len(results))
            return results

        except Exception as e:
            logger.error("Gene overlap GO suggestion failed: %s", e)
            return []

    def _combine_go_scores(
        self,
        embedding_scores: List[Dict],
        gene_scores: List[Dict]
    ) -> List[Dict]:
        """
        Combine embedding and gene scores with hybrid weighting

        Returns merged list with hybrid_score computed from both signals.
        """
        # Get weights from config
        go_config = getattr(self.config, 'go_suggestion', None)
        if go_config:
            weights_cfg = getattr(go_config, 'hybrid_weights', {})
            if isinstance(weights_cfg, dict):
                emb_weight = weights_cfg.get('embedding', 0.55)
                gene_weight = weights_cfg.get('gene', 0.45)
                bonus = weights_cfg.get('multi_evidence_bonus', 0.05)
            else:
                emb_weight = 0.55
                gene_weight = 0.45
                bonus = 0.05
        else:
            emb_weight = 0.55
            gene_weight = 0.45
            bonus = 0.05

        min_threshold = getattr(go_config, 'min_threshold', 0.15) if go_config else 0.15

        results = combine_scored_items(
            scored_lists={'text': embedding_scores, 'gene': gene_scores},
            id_field='go_id',
            weights={'text': emb_weight, 'gene': gene_weight},
            score_field_map={'text': 'text_similarity', 'gene': 'gene_overlap'},
            multi_evidence_bonus=bonus,
            min_threshold=min_threshold,
        )

        # Restore per-signal scores and gene data from signal_scores / _signal_data
        for item in results:
            sig = item.pop('signal_scores', {})
            sig_data = item.pop('_signal_data', {})
            item['text_similarity'] = round(sig.get('text', 0.0), 4)
            item['gene_overlap'] = round(sig.get('gene', 0.0), 4)

            # With "first writer wins", if embedding was first the base item
            # has matching_genes: []. Restore from gene signal's actual data.
            gene_data = sig_data.get('gene', {})
            if gene_data.get('matching_genes'):
                item['matching_genes'] = gene_data['matching_genes']

            # Restore go_gene_count from gene signal (most accurate)
            if gene_data.get('go_gene_count'):
                item['go_gene_count'] = gene_data['go_gene_count']

            # Restore split embedding scores if available
            emb_data = sig_data.get('text', {})
            if emb_data.get('name_similarity') is not None:
                item['name_similarity'] = emb_data['name_similarity']
                item['definition_similarity'] = emb_data.get('definition_similarity', 0.0)

        return results
