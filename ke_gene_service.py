"""
Shared service for extracting HGNC gene symbols from AOP-Wiki Key Events.

Used by both PathwaySuggestionService and GoSuggestionService.
"""
import hashlib
import json
import logging
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


def get_genes_from_ke(
    ke_id: str,
    aop_wiki_endpoint: str,
    cache_model=None
) -> List[str]:
    """
    Extract HGNC gene symbols associated with a Key Event via AOP-Wiki SPARQL.

    Args:
        ke_id: Key Event ID (e.g., "Event:123" or "KE 55")
        aop_wiki_endpoint: AOP-Wiki SPARQL endpoint URL
        cache_model: Optional cache model with get_cached_response/cache_response methods

    Returns:
        List of HGNC gene symbols
    """
    try:
        sparql_query = f"""
        PREFIX aopo: <http://aopkb.org/aop_ontology#>
        PREFIX edam: <http://edamontology.org/>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?keid ?ketitle ?hgnc
        WHERE {{
            ?ke a aopo:KeyEvent;
                edam:data_1025 ?object;
                dc:title ?ketitle;
                rdfs:label ?keid.
            ?object edam:data_2298 ?hgnc.
            FILTER(?keid = "{ke_id}")
        }}
        """

        # Check cache first
        query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
        if cache_model:
            cached_response = cache_model.get_cached_response(
                aop_wiki_endpoint, query_hash
            )
            if cached_response:
                logger.info("Serving KE genes from cache for %s", ke_id)
                return json.loads(cached_response)

        response = requests.post(
            aop_wiki_endpoint,
            data={"query": sparql_query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            genes = []

            if "results" in data and "bindings" in data["results"]:
                for binding in data["results"]["bindings"]:
                    if "hgnc" in binding:
                        gene = binding["hgnc"]["value"]
                        if gene and gene not in genes:
                            genes.append(gene)

            # Cache the results
            if cache_model:
                cache_model.cache_response(
                    aop_wiki_endpoint, query_hash, json.dumps(genes), 24
                )

            logger.info("Found %d genes for KE %s: %s", len(genes), ke_id, genes)
            return genes
        else:
            logger.error(
                "AOP-Wiki gene query failed: %s - %s", response.status_code, response.text
            )
            return []

    except Exception as e:
        logger.error("Error extracting genes from KE %s: %s", ke_id, e)
        return []
