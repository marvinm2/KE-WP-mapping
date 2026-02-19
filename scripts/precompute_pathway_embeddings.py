"""
Pre-compute BioBERT embeddings for all WikiPathways

Usage:
    python scripts/precompute_pathway_embeddings.py

Output:
    pathway_embeddings.npz - NPZ file with 'ids' (Unicode) and 'matrix' (float32, normalized)
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.services.embedding import BiologicalEmbeddingService
from src.core.models import Database, CacheModel
from src.core.config_loader import ConfigLoader
import logging
from tqdm import tqdm

# Import shared save utility (writes NPZ with normalized matrix)
from scripts.embedding_utils import save_embeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def precompute_all_pathway_embeddings(output_path='data/pathway_embeddings.npz'):
    """
    Fetch all WikiPathways and pre-compute their BioBERT embeddings
    """
    logger.info("Initializing services...")

    # Initialize embedding service
    embedding_service = BiologicalEmbeddingService()

    # Initialize database and cache model
    from src.core.config import Config
    config = Config()
    db = Database(config.DATABASE_PATH)
    cache_model = CacheModel(db)

    # Use existing pathway suggestion service to fetch all pathways
    logger.info("Fetching all WikiPathways...")

    from src.suggestions.pathway import PathwaySuggestionService

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

    # Save to disk using shared utility (NPZ format, pre-normalized vectors)
    save_embeddings(embeddings, output_path)


if __name__ == '__main__':
    precompute_all_pathway_embeddings()
