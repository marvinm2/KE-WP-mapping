"""
Pre-compute BioBERT embeddings for all Key Events from AOP-Wiki

Usage:
    python scripts/precompute_ke_embeddings.py

Output:
    ke_embeddings.npy - NumPy dictionary {ke_id: embedding_vector}
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from embedding_service import BiologicalEmbeddingService
from text_utils import remove_directionality_terms
import numpy as np
import logging
import requests
import re
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AOP-Wiki SPARQL endpoint
AOPWIKI_SPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"


def fetch_all_kes():
    """Fetch all Key Events from AOP-Wiki SPARQL endpoint"""
    sparql_query = """
    PREFIX aopo: <http://aopkb.org/aop_ontology#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX nci: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>

    SELECT DISTINCT ?KElabel ?KEtitle ?KEdescription ?biolevel
    WHERE {
      ?KE a aopo:KeyEvent ;
          dc:title ?KEtitle ;
          rdfs:label ?KElabel .
      OPTIONAL { ?KE dc:description ?KEdescription }
      OPTIONAL { ?KE nci:C25664 ?biolevel }
    }
    """

    try:
        response = requests.post(
            AOPWIKI_SPARQL_ENDPOINT,
            data={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=60
        )
        response.raise_for_status()

        results = response.json()['results']['bindings']

        # Extract KE data
        kes = []
        for result in results:
            # Extract KE ID from label
            ke_label = result['KElabel']['value']
            match = re.search(r'(\d+)$', ke_label)
            ke_id = f"KE {match.group(1)}" if match else ke_label

            ke_data = {
                'ke_id': ke_id,
                'ke_title': result['KEtitle']['value'],
                'ke_description': result.get('KEdescription', {}).get('value', ''),
                'biolevel': result.get('biolevel', {}).get('value', '')
            }
            kes.append(ke_data)

        logger.info(f"Fetched {len(kes)} Key Events from AOP-Wiki")
        return kes

    except Exception as e:
        logger.error(f"Failed to fetch KEs from AOP-Wiki: {e}")
        raise


def precompute_all_ke_embeddings(output_path='ke_embeddings.npy'):
    """
    Fetch all Key Events and pre-compute their BioBERT embeddings
    """
    logger.info("Initializing BioBERT service...")

    # Initialize embedding service
    embedding_service = BiologicalEmbeddingService()

    # Fetch all Key Events
    logger.info("Fetching all Key Events from AOP-Wiki...")
    kes = fetch_all_kes()

    # Compute embeddings
    embeddings = {}
    logger.info("Computing embeddings...")

    for ke in tqdm(kes, desc="Encoding Key Events"):
        ke_id = ke['ke_id']

        # IMPORTANT: Strip directionality terms from title before encoding
        ke_title_clean = remove_directionality_terms(ke['ke_title'])

        # Combine cleaned title + description (same as runtime logic)
        ke_text = f"{ke_title_clean}. {ke['ke_description']}" if ke['ke_description'] else ke_title_clean

        # Log first 3 samples for verification
        if len(embeddings) < 3:
            logger.info(f"Sample KE {ke_id}: '{ke['ke_title']}' -> '{ke_title_clean}'")

        # Compute embedding
        emb = embedding_service.encode(ke_text)
        embeddings[ke_id] = emb

    # Save to disk
    logger.info(f"Saving to {output_path}...")
    np.save(output_path, embeddings)

    logger.info(f"✓ Pre-computed {len(embeddings)} KE embeddings")
    logger.info(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

    # Print sample for verification
    sample_ke = list(embeddings.keys())[0]
    logger.info(f"Sample KE: {sample_ke}, embedding shape: {embeddings[sample_ke].shape}")


if __name__ == '__main__':
    precompute_all_ke_embeddings()
