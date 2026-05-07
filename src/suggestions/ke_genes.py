"""
Shared service for extracting persistent gene identifiers from AOP-Wiki Key Events.

Used by both PathwaySuggestionService and GoSuggestionService (and indirectly the
Reactome and GO suggestion services). Returns a strict-shape list of dicts
``{ncbi, hgnc, symbol}`` so downstream consumers can match against either the
NCBI Gene ID, the HGNC accession, or the HGNC symbol without re-querying.
"""
import hashlib
import json
import logging
import re
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Allowlist for KE ID literals interpolated into SPARQL FILTER clauses.
# Accepts both AOP-Wiki "Event:1234" and legacy "KE 55" styles, plus dashes/underscores.
_KE_ID_ALLOWED = re.compile(r"^[A-Za-z0-9 :_\-]+$")


def get_genes_from_ke(
    ke_id: str,
    aop_wiki_endpoint: str,
    cache_model=None
) -> List[Dict[str, str]]:
    """
    Extract genes (NCBI Gene ID + HGNC accession + HGNC symbol) for a Key Event.

    Args:
        ke_id: Key Event ID (e.g., "Event:123" or "KE 55")
        aop_wiki_endpoint: AOP-Wiki SPARQL endpoint URL
        cache_model: Optional cache model with get_cached_response/cache_response methods

    Returns:
        List of dicts with strict shape {"ncbi": str, "hgnc": str, "symbol": str}.
        Genes missing any of the three identifiers are dropped silently (Phase 28 D-04).
    """
    if not ke_id or not _KE_ID_ALLOWED.match(ke_id):
        logger.warning("Rejecting invalid KE ID for SPARQL interpolation: %r", ke_id)
        return []

    try:
        sparql_query = f"""
        # ke-genes-query-v2 — returns ncbi+hgnc+symbol triples (Phase 28)
        PREFIX aopo: <http://aopkb.org/aop_ontology#>
        PREFIX edam: <http://edamontology.org/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl:  <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT ?keid ?hgnc ?symbol ?ncbi
        WHERE {{
            ?ke a aopo:KeyEvent;
                edam:data_1025 ?gene;
                rdfs:label ?keid.
            ?gene edam:data_2298 ?hgnc;
                  rdfs:label ?symbol;
                  owl:sameAs ?ncbi.
            FILTER(?keid = "{ke_id}")
            FILTER(STRSTARTS(STR(?ncbi), "https://identifiers.org/ncbigene/"))
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
            genes: List[Dict[str, str]] = []
            seen = set()

            for binding in data.get("results", {}).get("bindings", []):
                try:
                    hgnc = binding["hgnc"]["value"].strip()
                    symbol = binding["symbol"]["value"].strip()
                    ncbi_iri = binding["ncbi"]["value"].strip()
                except KeyError:
                    continue  # D-04 strict skip — missing any of the three fields

                if not (hgnc and symbol and ncbi_iri):
                    continue  # D-04 strict skip — empty literal

                ncbi = ncbi_iri.rsplit("/", 1)[-1].strip()
                if not ncbi:
                    continue

                key = (ncbi, hgnc, symbol)
                if key in seen:
                    continue
                seen.add(key)
                genes.append({"ncbi": ncbi, "hgnc": hgnc, "symbol": symbol})

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

    except Exception:
        # Keep returning [] for backward compatibility with consumers that treat
        # the helper as fail-soft, but emit a full traceback so silent fetch /
        # parse failures stay distinguishable from "KE genuinely has no genes."
        logger.exception("Error extracting genes from KE %s", ke_id)
        return []
