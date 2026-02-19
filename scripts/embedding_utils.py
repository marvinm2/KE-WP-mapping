"""
Shared utilities for pre-compute embedding scripts.

Provides common setup, embedding computation, and save routines
used by precompute_ke_embeddings.py, precompute_pathway_title_embeddings.py,
and precompute_go_embeddings.py.
"""
import json
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
    from src.services.embedding import BiologicalEmbeddingService

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


def save_embeddings(embeddings: dict, path: str):
    """
    Save embeddings dict as NPZ matrix format with pre-normalized vectors (no pickle).

    Format: two arrays in the .npz file:
      - 'ids': 1D Unicode string array of embedding keys (dtype=str, NOT dtype=object)
      - 'matrix': 2D float32 array of shape (N, embedding_dim), each row unit-normalized

    Pre-normalization means dot product == cosine similarity at query time (no per-query
    norm computation needed). Using dtype=str for ids avoids pickle requirement on load.

    Args:
        embeddings: Dict mapping ID string -> numpy embedding vector
        path: Output path (accepts .npy or no extension; always writes .npz)
    """
    if not embeddings:
        logger.warning("save_embeddings called with empty dict, skipping save")
        return

    # Always write to .npz extension regardless of input path
    npz_path = path.replace('.npy', '').rstrip('.')

    # Build ids array with Unicode dtype (NOT dtype=object — that requires pickle on load)
    ids = np.array(list(embeddings.keys()), dtype=str)

    # Build and normalize matrix
    matrix = np.array(list(embeddings.values()), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # Guard against zero vectors (avoid division by zero)
    norms = np.where(norms == 0.0, 1.0, norms)
    matrix = (matrix / norms).astype(np.float32)

    logger.info("Saving %d normalized embeddings to %s.npz ...", len(embeddings), npz_path)
    np.savez(npz_path, ids=ids, matrix=matrix)

    actual_path = npz_path + '.npz'
    file_size_mb = os.path.getsize(actual_path) / 1024 / 1024
    logger.info("Saved: %.2f MB (shape: %s)", file_size_mb, str(matrix.shape))

    sample_id = next(iter(embeddings))
    logger.info("Sample id: %s, vector norm after normalization: %.6f",
                sample_id, float(np.linalg.norm(matrix[0])))


def save_metadata(metadata, path):
    """
    Save metadata list/dict to JSON file with size reporting.

    Args:
        metadata: List or dict to serialize
        path: Output file path
    """
    logger.info(f"Saving metadata to {path}...")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    file_size_mb = os.path.getsize(path) / 1024 / 1024
    count = len(metadata)
    logger.info(f"Saved {count} entries: {file_size_mb:.2f} MB")
