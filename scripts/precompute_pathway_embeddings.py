"""
Pre-compute BioBERT embeddings for all WikiPathways

Usage:
    python scripts/precompute_pathway_embeddings.py

Output:
    pathway_embeddings.npy - NumPy dictionary {pathway_id: embedding_vector}
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from embedding_service import BiologicalEmbeddingService
from models import Database, CacheModel
from config_loader import ConfigLoader
import numpy as np
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def precompute_all_pathway_embeddings(output_path='pathway_embeddings.npy'):
    """
    Fetch all WikiPathways and pre-compute their BioBERT embeddings
    """
    logger.info("Initializing services...")

    # Initialize embedding service
    embedding_service = BiologicalEmbeddingService()

    # Initialize database and cache model
    from config import Config
    config = Config()
    db = Database(config.DATABASE_PATH)
    cache_model = CacheModel(db)

    # Use existing pathway suggestion service to fetch all pathways
    logger.info("Fetching all WikiPathways...")

    from pathway_suggestions import PathwaySuggestionService

    # Load scoring config
    scoring_config = ConfigLoader.load_config()

    # Initialize pathway service
    pathway_service = PathwaySuggestionService(
        cache_model=cache_model,
        config=scoring_config,
        embedding_service=None  # We don't need embeddings for fetching
    )

    try:
        # Use the existing method to get all pathways
        pathways = pathway_service._get_all_pathways_for_search()
        logger.info(f"Found {len(pathways)} pathways")

    except Exception as e:
        logger.error(f"Failed to fetch pathways: {e}")
        import traceback
        traceback.print_exc()
        return

    # Compute embeddings
    embeddings = {}
    logger.info("Computing embeddings...")

    for pathway in tqdm(pathways, desc="Encoding pathways"):
        pathway_id = pathway['pathwayID']
        pathway_text = f"{pathway['pathwayTitle']}. {pathway.get('pathwayDescription', '')}"

        # Compute embedding
        emb = embedding_service.encode(pathway_text)
        embeddings[pathway_id] = emb

    # Save to disk
    logger.info(f"Saving to {output_path}...")
    np.save(output_path, embeddings)

    logger.info(f"✓ Pre-computed {len(embeddings)} pathway embeddings")
    logger.info(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


if __name__ == '__main__':
    precompute_all_pathway_embeddings()
