"""
Pre-compute BioBERT embeddings for all Key Events from AOP-Wiki

Usage:
    python scripts/precompute_ke_embeddings.py

Output:
    ke_embeddings.npy - NumPy dictionary {ke_id: embedding_vector}
"""

import re
import logging
import requests

from embedding_utils import setup_project_path, init_embedding_service, compute_embeddings_batch, save_embeddings, save_metadata

setup_project_path()

from text_utils import remove_directionality_terms

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

    SELECT DISTINCT ?KElabel ?KEtitle ?KEdescription ?biolevel ?KEpage
    WHERE {
      ?KE a aopo:KeyEvent ;
          dc:title ?KEtitle ;
          rdfs:label ?KElabel ;
          foaf:page ?KEpage .
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
                'biolevel': result.get('biolevel', {}).get('value', ''),
                'ke_page': result.get('KEpage', {}).get('value', '')
            }
            kes.append(ke_data)

        logger.info(f"Fetched {len(kes)} Key Events from AOP-Wiki")
        return kes

    except Exception as e:
        logger.error(f"Failed to fetch KEs from AOP-Wiki: {e}")
        raise


def precompute_all_ke_embeddings(output_path='ke_embeddings.npy',
                                  metadata_path='ke_metadata.json'):
    """
    Fetch all Key Events and pre-compute their BioBERT embeddings.
    Also saves ke_metadata.json for serving dropdown options without live SPARQL.
    """
    embedding_service = init_embedding_service()

    # Fetch all Key Events
    logger.info("Fetching all Key Events from AOP-Wiki...")
    kes = fetch_all_kes()

    # Save metadata in the format expected by /get_ke_options
    metadata = [
        {
            'KElabel': ke['ke_id'],
            'KEtitle': ke['ke_title'],
            'KEdescription': ke['ke_description'],
            'biolevel': ke['biolevel'],
            'KEpage': ke['ke_page'],
        }
        for ke in kes
    ]
    save_metadata(metadata, metadata_path)

    # Build {id: text} dict with directionality removal
    items = {}
    for ke in kes:
        ke_title_clean = remove_directionality_terms(ke['ke_title'])
        ke_text = f"{ke_title_clean}. {ke['ke_description']}" if ke['ke_description'] else ke_title_clean
        items[ke['ke_id']] = ke_text

    embeddings = compute_embeddings_batch(embedding_service, items, label="Key Events")
    save_embeddings(embeddings, output_path)


if __name__ == '__main__':
    precompute_all_ke_embeddings()
