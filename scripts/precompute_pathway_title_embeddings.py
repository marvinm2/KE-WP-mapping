"""
Pre-compute BioBERT embeddings for pathway titles (title-only)

This script generates a separate embedding file for pathway TITLES only,
to accelerate the compute_ke_pathway_similarity() title-to-title comparison.

Usage:
    python scripts/precompute_pathway_title_embeddings.py

Output:
    pathway_title_embeddings.npy - NumPy dictionary {pathway_id: title_embedding_vector}
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from embedding_service import BiologicalEmbeddingService
import numpy as np
import logging
import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WikiPathways SPARQL endpoint
WIKIPATHWAYS_SPARQL_ENDPOINT = "https://sparql.wikipathways.org/sparql"


def fetch_all_pathways():
    """Fetch all WikiPathways from SPARQL endpoint"""
    sparql_query = """
    PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>

    SELECT DISTINCT ?pathway ?pathwayTitle
    WHERE {
        ?pathway a wp:Pathway ;
                dc:title ?pathwayTitle ;
                wp:organism ?organism .

        FILTER(?organism = <http://purl.obolibrary.org/obo/NCBITaxon_9606>)
    }
    """

    try:
        response = requests.post(
            WIKIPATHWAYS_SPARQL_ENDPOINT,
            data={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=60
        )
        response.raise_for_status()

        results = response.json()['results']['bindings']

        # Extract pathway data
        pathways = []
        for result in results:
            pathway_uri = result['pathway']['value']
            # Extract pathway ID from URI and remove revision number (e.g., WP5482_r129257 -> WP5482)
            pathway_id_full = pathway_uri.split('/')[-1]
            pathway_id = pathway_id_full.split('_')[0]  # Remove revision number

            pathway_data = {
                'pathwayID': pathway_id,
                'pathwayTitle': result['pathwayTitle']['value']
            }
            pathways.append(pathway_data)

        logger.info(f"Fetched {len(pathways)} pathways from WikiPathways")
        return pathways

    except Exception as e:
        logger.error(f"Failed to fetch pathways from WikiPathways: {e}")
        raise


def precompute_pathway_title_embeddings(output_path='pathway_title_embeddings.npy'):
    """
    Fetch all WikiPathways and pre-compute their title-only BioBERT embeddings
    """
    logger.info("Initializing BioBERT service...")

    # Initialize embedding service
    embedding_service = BiologicalEmbeddingService()

    # Fetch all pathways
    logger.info("Fetching all pathways from WikiPathways...")
    pathways = fetch_all_pathways()

    # Remove duplicates (keep first occurrence of each pathway ID)
    seen_ids = set()
    unique_pathways = []
    for pathway in pathways:
        if pathway['pathwayID'] not in seen_ids:
            unique_pathways.append(pathway)
            seen_ids.add(pathway['pathwayID'])

    logger.info(f"After removing duplicates: {len(unique_pathways)} unique pathways")

    # Compute title embeddings
    embeddings = {}
    logger.info("Computing title embeddings...")

    for pathway in tqdm(unique_pathways, desc="Encoding pathway titles"):
        pathway_id = pathway['pathwayID']
        pathway_title = pathway['pathwayTitle']

        # Log first 3 samples for verification
        if len(embeddings) < 3:
            logger.info(f"Sample pathway {pathway_id}: '{pathway_title}'")

        # Encode title only
        emb = embedding_service.encode(pathway_title)
        embeddings[pathway_id] = emb

    # Save to disk
    logger.info(f"Saving to {output_path}...")
    np.save(output_path, embeddings)

    logger.info(f"✓ Pre-computed {len(embeddings)} pathway title embeddings")
    logger.info(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

    # Print sample for verification
    sample_id = list(embeddings.keys())[0]
    logger.info(f"Sample pathway: {sample_id}, embedding shape: {embeddings[sample_id].shape}")


if __name__ == '__main__':
    precompute_pathway_title_embeddings()
