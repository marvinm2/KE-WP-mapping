"""
GMT file generation for KE-WP and KE-GO mapping types.

Pure Python module — no Flask dependency. Called by routes in later plans.
"""
import io
import json
import logging
import os
import re
import unicodedata
from collections import defaultdict

logger = logging.getLogger(__name__)

WIKIPATHWAYS_SPARQL = "https://sparql.wikipathways.org/sparql"


def _make_ke_slug(ke_id: str, ke_title: str) -> str:
    """Return KE{N}_{Title_Slug} without a target suffix.

    Examples:
        _make_ke_slug('KE 55', 'Decreased BDNF Expression') -> 'KE55_Decreased_BDNF_Expression'
    """
    num = re.sub(r'\D', '', ke_id)
    # Normalise unicode -> ASCII, then keep only alphanumeric/underscore chars
    normalized = unicodedata.normalize("NFKD", ke_title).encode("ascii", "ignore").decode("ascii")
    title_slug = re.sub(r'[^a-zA-Z0-9]+', '_', normalized).strip('_')
    return f"KE{num}_{title_slug}"


def _parse_gene_bindings(data: dict) -> dict:
    """Parse SPARQL JSON result bindings into {pathway_id: [gene_symbol, ...]}."""
    result = {}
    for binding in data.get("results", {}).get("bindings", []):
        pid = binding.get("pathwayID", {}).get("value", "")
        gene = binding.get("geneSymbol", {}).get("value", "")
        if pid and gene:
            result.setdefault(pid, []).append(gene)
    return result


def _fetch_pathway_genes_batch(wp_ids: list, cache_model=None) -> dict:
    """Return {wp_id: [hgnc_symbol, ...]} for all given wp_ids.

    Issues a single SPARQL VALUES query to WikiPathways for all IDs at once.
    Silently returns an empty dict on any failure.
    """
    if not wp_ids:
        return {}
    import hashlib
    import requests

    values_clause = " ".join([f'"{wid}"' for wid in wp_ids])
    query = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT DISTINCT ?pathwayID ?geneSymbol WHERE {{
  ?pathway a wp:Pathway ;
           dcterms:identifier ?pathwayID .
  ?geneProduct dcterms:isPartOf ?pathway ;
               wp:bdbHgncSymbol ?geneSymbolIRI .
  BIND(STRAFTER(STR(?geneSymbolIRI), "hgnc.symbol/") AS ?geneSymbol)
  VALUES ?pathwayID {{ {values_clause} }}
}}
"""
    query_hash = hashlib.md5(query.encode()).hexdigest()

    # Try cache first
    if cache_model:
        cached = cache_model.get_cached_response(WIKIPATHWAYS_SPARQL, query_hash)
        if cached:
            data = json.loads(cached)
            return _parse_gene_bindings(data)

    try:
        resp = requests.post(
            WIKIPATHWAYS_SPARQL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if cache_model:
            cache_model.cache_response(WIKIPATHWAYS_SPARQL, query_hash, resp.text, expiry_hours=24)
        return _parse_gene_bindings(data)
    except Exception as e:
        logger.warning("WikiPathways SPARQL batch gene fetch failed: %s", e)
        return {}


def generate_ke_wp_gmt(mappings, cache_model=None, min_confidence=None) -> str:
    """Generate GMT content for KE-WP mappings.

    Parameters
    ----------
    mappings:
        List of dicts from MappingModel.get_all_mappings(). Each dict must
        contain at least: ke_id, ke_title, wp_id, wp_title, confidence_level.
    cache_model:
        Optional CacheModel instance for SPARQL result caching. Pass None to
        skip caching.
    min_confidence:
        Optional lowercase string (e.g. "high"). Rows whose confidence_level
        does not match are excluded.

    Returns
    -------
    str
        GMT-formatted string (tab-separated, one row per KE-pathway pair).
        Empty string if no rows survive filtering or no genes are found.
    """
    # Apply confidence filter
    if min_confidence:
        mappings = [
            r for r in mappings
            if r.get("confidence_level", "").lower() == min_confidence
        ]

    if not mappings:
        return ""

    # Collect unique WP IDs for batch SPARQL
    wp_ids = list(dict.fromkeys(r["wp_id"] for r in mappings))
    genes_by_wp = _fetch_pathway_genes_batch(wp_ids, cache_model=cache_model)

    buf = io.StringIO()
    for row in mappings:
        wp_id = row["wp_id"]
        genes = genes_by_wp.get(wp_id, [])
        if not genes:
            # GMT convention: skip rows with no genes
            continue
        # Deduplicate while preserving order
        genes = list(dict.fromkeys(genes))
        ke_slug = _make_ke_slug(row["ke_id"], row["ke_title"])
        term_name = f"{ke_slug}_{wp_id}"
        description = row["wp_title"]
        line = "\t".join([term_name, description] + genes)
        buf.write(line + "\n")

    return buf.getvalue()


def generate_ke_go_gmt(mappings, go_annotations_path=None, min_confidence=None) -> str:
    """Generate GMT content for KE-GO mappings.

    Parameters
    ----------
    mappings:
        List of dicts from GoMappingModel.get_all_mappings(). Each dict must
        contain at least: ke_id, ke_title, go_id, go_name, confidence_level.
    go_annotations_path:
        Path to go_bp_gene_annotations.json. Defaults to
        data/go_bp_gene_annotations.json relative to the project root.
    min_confidence:
        Optional lowercase string for confidence filtering.

    Returns
    -------
    str
        GMT-formatted string. Empty string if no rows survive.
    """
    if go_annotations_path is None:
        go_annotations_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'go_bp_gene_annotations.json'
        )

    # Load GO gene annotations
    try:
        with open(go_annotations_path) as f:
            go_annotations = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load GO annotations from %s: %s", go_annotations_path, e)
        go_annotations = {}

    # Apply confidence filter
    if min_confidence:
        mappings = [
            r for r in mappings
            if r.get("confidence_level", "").lower() == min_confidence
        ]

    if not mappings:
        return ""

    buf = io.StringIO()
    for row in mappings:
        go_id = row["go_id"]
        genes = go_annotations.get(go_id, [])
        if not genes:
            # Skip rows with no annotation entry
            continue
        # Deduplicate while preserving order
        genes = list(dict.fromkeys(genes))
        ke_slug = _make_ke_slug(row["ke_id"], row["ke_title"])
        term_name = f"{ke_slug}_{go_id}"
        description = row["go_name"]
        line = "\t".join([term_name, description] + genes)
        buf.write(line + "\n")

    return buf.getvalue()


def generate_ke_centric_wp_gmt(mappings, cache_model=None, min_confidence=None) -> str:
    """Generate KE-centric GMT content for KE-WP mappings.

    Each row represents one Key Event. Gene symbols are unioned across all
    approved WikiPathways mappings for that KE. Field 1 is just ``KE{N}``
    (e.g. ``KE55``), not the full slug — suitable for KE-level enrichment
    testing with fgsea or clusterProfiler.

    Parameters
    ----------
    mappings:
        List of dicts from MappingModel.get_all_mappings(). Each dict must
        contain at least: ke_id, ke_title, wp_id, confidence_level.
    cache_model:
        Optional CacheModel instance for SPARQL result caching.
    min_confidence:
        Optional lowercase string (e.g. "high"). Rows whose confidence_level
        does not match are excluded.

    Returns
    -------
    str
        GMT-formatted string (tab-separated, one row per KE).
        Empty string if no rows survive filtering or no genes are found.
    """
    if min_confidence:
        mappings = [r for r in mappings if r.get("confidence_level", "").lower() == min_confidence]

    if not mappings:
        return ""

    # Group WP IDs by KE, preserving KE metadata
    ke_to_wps = defaultdict(list)
    ke_meta = {}
    for row in mappings:
        ke_to_wps[row["ke_id"]].append(row["wp_id"])
        ke_meta[row["ke_id"]] = (row["ke_id"], row["ke_title"])

    # Collect all unique WP IDs for a single batch SPARQL call
    all_wp_ids = list(dict.fromkeys(wp for wps in ke_to_wps.values() for wp in wps))
    genes_by_wp = _fetch_pathway_genes_batch(all_wp_ids, cache_model=cache_model)

    buf = io.StringIO()
    for ke_id in sorted(ke_to_wps.keys(), key=lambda k: int(re.sub(r'\D', '', k) or '0')):
        all_genes = []
        for wp_id in ke_to_wps[ke_id]:
            all_genes.extend(genes_by_wp.get(wp_id, []))
        genes = list(dict.fromkeys(all_genes))  # deduplicate, preserve order
        if not genes:
            continue
        ke_id_raw, ke_title = ke_meta[ke_id]
        num = re.sub(r'\D', '', ke_id_raw)
        term_name = f"KE{num}"  # Field 1: JUST "KE55" — locked decision
        description = ke_title  # Field 2: KE title
        line = "\t".join([term_name, description] + genes)
        buf.write(line + "\n")

    return buf.getvalue()


def generate_ke_centric_go_gmt(mappings, go_annotations_path=None, min_confidence=None) -> str:
    """Generate KE-centric GMT content for KE-GO mappings.

    Each row represents one Key Event. Gene symbols are unioned across all
    approved GO Biological Process mappings for that KE. Field 1 is just
    ``KE{N}`` (e.g. ``KE55``).

    Parameters
    ----------
    mappings:
        List of dicts from GoMappingModel.get_all_mappings(). Each dict must
        contain at least: ke_id, ke_title, go_id, confidence_level.
    go_annotations_path:
        Path to go_bp_gene_annotations.json. Defaults to
        data/go_bp_gene_annotations.json relative to the project root.
    min_confidence:
        Optional lowercase string for confidence filtering.

    Returns
    -------
    str
        GMT-formatted string (tab-separated, one row per KE).
        Empty string if no rows survive filtering or no genes are found.
    """
    if go_annotations_path is None:
        go_annotations_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'go_bp_gene_annotations.json'
        )

    try:
        with open(go_annotations_path) as f:
            go_annotations = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load GO annotations from %s: %s", go_annotations_path, e)
        go_annotations = {}

    if min_confidence:
        mappings = [r for r in mappings if r.get("confidence_level", "").lower() == min_confidence]

    if not mappings:
        return ""

    # Group GO IDs by KE, preserving KE metadata
    ke_to_gos = defaultdict(list)
    ke_meta = {}
    for row in mappings:
        ke_to_gos[row["ke_id"]].append(row["go_id"])
        ke_meta[row["ke_id"]] = (row["ke_id"], row["ke_title"])

    buf = io.StringIO()
    for ke_id in sorted(ke_to_gos.keys(), key=lambda k: int(re.sub(r'\D', '', k) or '0')):
        all_genes = []
        for go_id in ke_to_gos[ke_id]:
            all_genes.extend(go_annotations.get(go_id, []))
        genes = list(dict.fromkeys(all_genes))  # deduplicate, preserve order
        if not genes:
            continue
        ke_id_raw, ke_title = ke_meta[ke_id]
        num = re.sub(r'\D', '', ke_id_raw)
        term_name = f"KE{num}"  # Field 1: JUST "KE55" — locked decision
        description = ke_title  # Field 2: KE title
        line = "\t".join([term_name, description] + genes)
        buf.write(line + "\n")

    return buf.getvalue()
