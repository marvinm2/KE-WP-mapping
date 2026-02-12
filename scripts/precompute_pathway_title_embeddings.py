"""
Pre-compute BioBERT embeddings for pathway titles (title-only) WITH entity extraction

This script generates embeddings for pathway TITLES with entity extraction applied,
removing directionality terms and focusing on biological entities for more specific matching.

Usage:
    python scripts/precompute_pathway_title_embeddings.py

Output:
    pathway_title_embeddings.npy - NumPy dictionary {pathway_id: title_embedding_vector}
"""

import logging
import requests

from embedding_utils import setup_project_path, init_embedding_service, compute_embeddings_batch, save_embeddings, save_metadata

setup_project_path()

from text_utils import remove_directionality_terms, extract_entities

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

    SELECT DISTINCT ?pathway ?pathwayTitle ?pathwayLink ?pathwayDescription
    WHERE {
        ?pathway a wp:Pathway ;
                dc:title ?pathwayTitle ;
                dc:identifier ?pathwayLink ;
                wp:organismName "Homo sapiens" .
        OPTIONAL { ?pathway dcterms:description ?pathwayDescription }
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
                'pathwayTitle': result['pathwayTitle']['value'],
                'pathwayLink': result.get('pathwayLink', {}).get('value', ''),
                'pathwayDescription': result.get('pathwayDescription', {}).get('value', '')
            }
            pathways.append(pathway_data)

        logger.info(f"Fetched {len(pathways)} pathways from WikiPathways")
        return pathways

    except Exception as e:
        logger.error(f"Failed to fetch pathways from WikiPathways: {e}")
        raise


def fetch_pathway_ontology_tags():
    """Fetch pathway ontology tags from WikiPathways"""
    sparql_query = """
    PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?pathwayID ?termLabel
    WHERE {
        ?pathway a wp:Pathway ;
                 dcterms:identifier ?pathwayID ;
                 wp:organismName "Homo sapiens" ;
                 wp:pathwayOntologyTag ?ontologyTerm .
        ?ontologyTerm rdfs:label ?termLabel .
    }
    """

    try:
        response = requests.post(
            WIKIPATHWAYS_SPARQL_ENDPOINT,
            data={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=90
        )
        response.raise_for_status()

        results = response.json()['results']['bindings']

        # Group tags by pathway ID
        tags_by_pathway = {}
        for result in results:
            pathway_id = result['pathwayID']['value']
            tag_label = result['termLabel']['value']

            if pathway_id not in tags_by_pathway:
                tags_by_pathway[pathway_id] = []
            tags_by_pathway[pathway_id].append(tag_label)

        logger.info(f"Fetched ontology tags for {len(tags_by_pathway)} pathways")
        return tags_by_pathway

    except Exception as e:
        logger.warning(f"Failed to fetch pathway ontology tags: {e}")
        return {}


def fetch_pathway_publications():
    """Fetch pathway publications from WikiPathways"""
    sparql_query = """
    PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?pathwayID ?pubmed
    WHERE {
        ?pathway a wp:Pathway ;
                 dcterms:identifier ?pathwayID ;
                 wp:organismName "Homo sapiens" .
        ?pathway ?p ?pubref .
        ?pubref ?pp ?pubmed .
        FILTER(CONTAINS(STR(?pubmed), "pubmed"))
    }
    """

    try:
        response = requests.post(
            WIKIPATHWAYS_SPARQL_ENDPOINT,
            data={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=90
        )
        response.raise_for_status()

        results = response.json()['results']['bindings']

        # Group publications by pathway ID
        pubs_by_pathway = {}
        for result in results:
            pathway_id = result['pathwayID']['value']
            pubmed_url = result['pubmed']['value']

            # Extract PMID from URL (e.g., http://www.ncbi.nlm.nih.gov/pubmed/34519429 -> 34519429)
            if 'pubmed/' in pubmed_url:
                pmid = pubmed_url.split('pubmed/')[-1]

                if pathway_id not in pubs_by_pathway:
                    pubs_by_pathway[pathway_id] = []

                # Store as dict with PMID and URL
                pubs_by_pathway[pathway_id].append({
                    'pmid': pmid,
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })

        logger.info(f"Fetched publications for {len(pubs_by_pathway)} pathways")
        return pubs_by_pathway

    except Exception as e:
        logger.warning(f"Failed to fetch pathway publications: {e}")
        return {}


def precompute_pathway_title_embeddings(output_path='pathway_title_embeddings.npy',
                                        metadata_path='pathway_metadata.json'):
    """
    Fetch all WikiPathways and pre-compute their title-only BioBERT embeddings.
    Also saves pathway_metadata.json for serving dropdown options without live SPARQL.
    """
    embedding_service = init_embedding_service()

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

    # Fetch enrichment data (ontology tags and publications)
    logger.info("Fetching pathway ontology tags...")
    ontology_tags = fetch_pathway_ontology_tags()

    logger.info("Fetching pathway publications...")
    publications = fetch_pathway_publications()

    # Merge enrichment data into pathway metadata
    for pathway in unique_pathways:
        pathway_id = pathway['pathwayID']

        # Add ontology tags (default to empty list if none found)
        pathway['ontologyTags'] = ontology_tags.get(pathway_id, [])

        # Add publications (default to empty list if none found)
        pathway['publications'] = publications.get(pathway_id, [])

    logger.info(f"Enriched {len(unique_pathways)} pathways with ontology tags and publications")

    # Save metadata in the format expected by /get_pathway_options
    save_metadata(unique_pathways, metadata_path)

    # Build {id: text} dict with directionality removal + entity extraction
    items = {}
    for pathway in unique_pathways:
        items[pathway['pathwayID']] = extract_entities(
            remove_directionality_terms(pathway['pathwayTitle'])
        )

    embeddings = compute_embeddings_batch(embedding_service, items, label="pathway titles")
    save_embeddings(embeddings, output_path)


if __name__ == '__main__':
    precompute_pathway_title_embeddings()
