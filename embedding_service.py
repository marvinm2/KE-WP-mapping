"""
BioBERT embedding service for semantic similarity computation
"""

from __future__ import annotations
from typing import List, Dict, Optional, TYPE_CHECKING
from functools import lru_cache
import logging
import os

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# Optional imports - only required when embeddings are enabled
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import torch
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("BioBERT dependencies not installed. Embedding service will be unavailable.")
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    np = None
    torch = None


class BiologicalEmbeddingService:
    """
    Service for computing semantic similarity using BioBERT embeddings

    Features:
    - LRU cache for recent encodings (1000 items)
    - Pre-computed pathway embeddings (loaded from disk)
    - Fallback to text-based matching on errors
    - GPU support (auto-detected)
    """

    def __init__(
        self,
        model_name: str = "dmis-lab/biobert-base-cased-v1.2",
        use_gpu: bool = True,
        precomputed_embeddings_path: Optional[str] = None,
        precomputed_ke_embeddings_path: Optional[str] = None
    ):
        """
        Initialize BioBERT model

        Args:
            model_name: HuggingFace model identifier
            use_gpu: Use GPU if available
            precomputed_embeddings_path: Path to .npy file with pathway embeddings
            precomputed_ke_embeddings_path: Path to .npy file with KE embeddings
        """
        if not EMBEDDINGS_AVAILABLE:
            raise RuntimeError(
                "BioBERT dependencies not installed. "
                "Install with: pip install transformers sentence-transformers torch"
            )

        try:
            device = 'cuda' if use_gpu and torch.cuda.is_available() else 'cpu'
            logger.info(f"Initializing BioBERT model on {device}")

            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
            self.device = device

            # Load pre-computed pathway embeddings if available
            self.pathway_embeddings = {}
            if precomputed_embeddings_path and os.path.exists(precomputed_embeddings_path):
                self._load_precomputed_embeddings(precomputed_embeddings_path)

            # Load pre-computed KE embeddings if available
            self.ke_embeddings = {}
            if precomputed_ke_embeddings_path and os.path.exists(precomputed_ke_embeddings_path):
                self._load_precomputed_ke_embeddings(precomputed_ke_embeddings_path)

            # Load pre-computed pathway TITLE embeddings if available
            self.pathway_title_embeddings = {}
            if os.path.exists('pathway_title_embeddings.npy'):
                self._load_precomputed_pathway_title_embeddings('pathway_title_embeddings.npy')

            logger.info(f"BioBERT service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize BioBERT: {e}")
            raise

    def _load_precomputed_embeddings(self, path: str):
        """Load pre-computed pathway embeddings from disk"""
        try:
            import numpy as np
            self.pathway_embeddings = np.load(path, allow_pickle=True).item()
            logger.info(f"Loaded {len(self.pathway_embeddings)} pre-computed pathway embeddings")
        except Exception as e:
            logger.warning(f"Could not load pre-computed embeddings: {e}")
            self.pathway_embeddings = {}

    def _load_precomputed_ke_embeddings(self, path: str):
        """Load pre-computed KE embeddings from disk"""
        try:
            import numpy as np
            self.ke_embeddings = np.load(path, allow_pickle=True).item()
            logger.info(f"Loaded {len(self.ke_embeddings)} pre-computed KE embeddings")
        except Exception as e:
            logger.warning(f"Could not load pre-computed KE embeddings: {e}")
            self.ke_embeddings = {}

    def _load_precomputed_pathway_title_embeddings(self, path: str):
        """Load pre-computed pathway title embeddings from disk"""
        try:
            import numpy as np
            self.pathway_title_embeddings = np.load(path, allow_pickle=True).item()
            logger.info(f"Loaded {len(self.pathway_title_embeddings)} pre-computed pathway title embeddings")
        except Exception as e:
            logger.warning(f"Could not load pre-computed pathway title embeddings: {e}")
            self.pathway_title_embeddings = {}

    @lru_cache(maxsize=1000)
    def encode(self, text: str) -> 'np.ndarray':
        """
        Encode text to embedding vector with caching

        Args:
            text: Input text (KE or pathway description)

        Returns:
            768-dimensional embedding vector
        """
        try:
            return self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            # Return zero vector as fallback
            return np.zeros(768)

    def get_pathway_embedding(self, pathway_id: str, pathway_text: str) -> 'np.ndarray':
        """
        Get embedding for pathway (uses pre-computed if available)

        Args:
            pathway_id: WikiPathways ID (e.g., "WP4269")
            pathway_text: Combined title + description

        Returns:
            Embedding vector
        """
        # Check pre-computed first
        if pathway_id in self.pathway_embeddings:
            return self.pathway_embeddings[pathway_id]

        # Otherwise, compute and cache
        return self.encode(pathway_text)

    def get_ke_embedding(self, ke_id: str, ke_text: str) -> 'np.ndarray':
        """
        Get embedding for Key Event (uses pre-computed if available)

        Args:
            ke_id: Key Event ID (e.g., "KE 55", "KE 1508")
            ke_text: Combined title + description

        Returns:
            Embedding vector
        """
        # Check pre-computed first
        if ke_id in self.ke_embeddings:
            return self.ke_embeddings[ke_id]

        # Otherwise, compute and cache via encode()
        return self.encode(ke_text)

    def compute_similarity(self, text1: str, text2: str, pathway_id: str = None) -> float:
        """
        Compute cosine similarity between two texts

        Args:
            text1: First text (e.g., KE title)
            text2: Second text (e.g., pathway title)
            pathway_id: Optional pathway ID for pre-computed lookup

        Returns:
            Similarity score 0.0-1.0 (normalized from -1 to 1)
        """
        try:
            # Encode first text (KE title)
            emb1 = self.encode(text1)

            # For pathway titles, use pre-computed if available
            if pathway_id and pathway_id in self.pathway_title_embeddings:
                emb2 = self.pathway_title_embeddings[pathway_id]
            else:
                emb2 = self.encode(text2)

            # Cosine similarity
            similarity = np.dot(emb1, emb2) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
            )

            # Normalize to 0-1 range (cosine can be -1 to 1)
            normalized = (similarity + 1.0) / 2.0

            return float(np.clip(normalized, 0.0, 1.0))

        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0

    def compute_ke_pathway_similarity(
        self,
        ke_title: str,
        ke_description: str,
        pathway_id: str,
        pathway_title: str,
        pathway_description: str
    ) -> Dict[str, float]:
        """
        Compute multi-level semantic similarity between KE and pathway

        Args:
            ke_title: Key Event title
            ke_description: Key Event description
            pathway_id: WikiPathways ID
            pathway_title: Pathway title
            pathway_description: Pathway description

        Returns:
            {
                'title_similarity': float,
                'description_similarity': float,
                'combined_similarity': float
            }
        """
        try:
            # Title-to-title similarity (NOW USES PRE-COMPUTED)
            title_sim = self.compute_similarity(ke_title, pathway_title, pathway_id=pathway_id)

            # Full text similarity (title + description)
            ke_text = f"{ke_title}. {ke_description}" if ke_description else ke_title
            pathway_text = f"{pathway_title}. {pathway_description}" if pathway_description else pathway_title

            # Use pre-computed pathway embedding if available
            ke_emb = self.encode(ke_text)
            pathway_emb = self.get_pathway_embedding(pathway_id, pathway_text)

            # Description-level similarity
            desc_sim = np.dot(ke_emb, pathway_emb) / (
                np.linalg.norm(ke_emb) * np.linalg.norm(pathway_emb) + 1e-8
            )
            desc_sim = float(np.clip((desc_sim + 1.0) / 2.0, 0.0, 1.0))

            # Combined: Title is more important (60/40 split)
            combined = (title_sim * 0.6) + (desc_sim * 0.4)

            return {
                'title_similarity': title_sim,
                'description_similarity': desc_sim,
                'combined_similarity': combined
            }

        except Exception as e:
            logger.error(f"KE-pathway similarity failed: {e}")
            return {
                'title_similarity': 0.0,
                'description_similarity': 0.0,
                'combined_similarity': 0.0
            }

    def compute_batch_similarity(
        self,
        query: str,
        candidates: List[str]
    ) -> List[float]:
        """
        Compute similarity between query and multiple candidates efficiently

        Args:
            query: Query text (e.g., KE description)
            candidates: List of candidate texts (pathway descriptions)

        Returns:
            List of similarity scores
        """
        try:
            query_emb = self.encode(query)
            candidate_embs = self.model.encode(
                candidates,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=32
            )

            # Batch cosine similarity
            similarities = np.dot(candidate_embs, query_emb) / (
                np.linalg.norm(candidate_embs, axis=1) * np.linalg.norm(query_emb) + 1e-8
            )

            # Normalize to 0-1
            normalized = (similarities + 1.0) / 2.0

            return [float(np.clip(s, 0.0, 1.0)) for s in normalized]

        except Exception as e:
            logger.error(f"Batch similarity failed: {e}")
            return [0.0] * len(candidates)
