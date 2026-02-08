"""
Shared utilities for pre-compute embedding scripts.

Provides common setup, embedding computation, and save routines
used by precompute_ke_embeddings.py, precompute_pathway_title_embeddings.py,
and precompute_go_embeddings.py.
"""
import os
import sys
import logging

import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)


def setup_project_path():
    """Add project root to sys.path so imports like embedding_service work."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def init_embedding_service():
    """
    Initialize BioBERT embedding service with standard config.

    Returns:
        BiologicalEmbeddingService instance
    """
    from embedding_service import BiologicalEmbeddingService

    logger.info("Initializing BioBERT service...")
    service = BiologicalEmbeddingService()
    return service


def compute_embeddings_batch(embedding_service, items, label="items"):
    """
    Compute embeddings for a dict of {id: text} with a progress bar.

    Args:
        embedding_service: BiologicalEmbeddingService instance
        items: Dict mapping ID -> text to embed
        label: Description for the progress bar

    Returns:
        Dict mapping ID -> numpy embedding vector
    """
    embeddings = {}
    sample_count = 0

    for item_id, text in tqdm(items.items(), desc=f"Encoding {label}"):
        # Log first 3 samples for verification
        if sample_count < 3:
            logger.info(f"Sample {item_id}: '{text[:80]}{'...' if len(text) > 80 else ''}'")
            sample_count += 1

        emb = embedding_service.encode(text)
        embeddings[item_id] = emb

    logger.info(f"Computed {len(embeddings)} embeddings for {label}")
    return embeddings


def save_embeddings(embeddings, path):
    """
    Save embeddings dict to .npy file with size reporting.

    Args:
        embeddings: Dict mapping ID -> numpy embedding vector
        path: Output file path
    """
    logger.info(f"Saving {len(embeddings)} embeddings to {path}...")
    np.save(path, embeddings)

    file_size_mb = os.path.getsize(path) / 1024 / 1024
    logger.info(f"Saved: {file_size_mb:.2f} MB")

    if embeddings:
        sample_id = next(iter(embeddings))
        logger.info(f"Sample: {sample_id}, shape: {embeddings[sample_id].shape}")
