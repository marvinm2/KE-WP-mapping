"""
Public REST API v1 Blueprint
Versioned, read-only, no authentication required.
Entirely separate from the internal api_bp.
"""
import csv
import hashlib
import io
import json
import logging
import math

import requests as requests_lib
from flask import Blueprint, jsonify, make_response, request

from src.utils.text import sanitize_log

logger = logging.getLogger(__name__)

v1_api_bp = Blueprint("v1_api", __name__, url_prefix="/api/v1")

# Module-level model references — set by app.py via set_models()
mapping_model = None
go_mapping_model = None
cache_model = None
ke_metadata_index = None
ke_aop_membership = None
go_hierarchy = None
go_bp_metadata = None


def set_models(mapping, go_mapping, cache, ke_meta_index=None,
               ke_aop_data=None, go_hier=None, go_bp_meta=None):
    """Inject model instances from create_app()."""
    global mapping_model, go_mapping_model, cache_model
    global ke_metadata_index, ke_aop_membership, go_hierarchy, go_bp_metadata
    mapping_model = mapping
    go_mapping_model = go_mapping
    cache_model = cache
    ke_metadata_index = ke_meta_index
    ke_aop_membership = ke_aop_data
    go_hierarchy = go_hier
    go_bp_metadata = go_bp_meta


# ---------------------------------------------------------------------------
# CORS — blueprint-scoped, does NOT affect internal api_bp
# ---------------------------------------------------------------------------

@v1_api_bp.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_pagination_params():
    """Parse and clamp ?page= and ?per_page= from request.args."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", 50))
        per_page = max(1, min(per_page, 200))
    except (ValueError, TypeError):
        per_page = 50
    return page, per_page


def _make_pagination(page, per_page, total, base_url, extra_params):
    """Build pagination envelope with absolute next/prev URLs."""
    total_pages = math.ceil(total / per_page) if per_page and total else 0

    from urllib.parse import urlencode

    def _page_url(p):
        params = {**extra_params, "page": p, "per_page": per_page}
        return f"{base_url}?{urlencode(params)}"

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "next": _page_url(page + 1) if page < total_pages else None,
        "prev": _page_url(page - 1) if page > 1 else None,
    }


def _serialize_mapping(row):
    """Convert a DB row dict to the v1 mapping object shape."""
    ke_id = row["ke_id"]

    # KE context enrichment
    aop_entries = (ke_aop_membership or {}).get(ke_id, [])
    ke_aop_context = [entry["aop_id"] for entry in aop_entries]

    ke_meta = (ke_metadata_index or {}).get(ke_id)
    ke_bio_level = ke_meta.get("biolevel") if ke_meta else None

    return {
        "uuid": row["uuid"],
        "ke_id": ke_id,
        "ke_name": row["ke_title"],
        "pathway_id": row["wp_id"],
        "pathway_title": row["wp_title"],
        "confidence_level": row["confidence_level"],
        "connection_type": row.get("connection_type"),
        "ke_aop_context": ke_aop_context,
        "ke_bio_level": ke_bio_level,
        "provenance": {
            "suggestion_score": row.get("suggestion_score"),
            "approved_by": row.get("approved_by_curator"),
            "approved_at": row.get("approved_at_curator"),
            "proposed_by": row.get("proposed_by"),
        },
    }


def _serialize_go_mapping(row):
    """Convert a DB row dict to the v1 GO mapping object shape."""
    ke_id = row["ke_id"]
    go_id = row["go_id"]

    # KE context enrichment
    aop_entries = (ke_aop_membership or {}).get(ke_id, [])
    ke_aop_context = [entry["aop_id"] for entry in aop_entries]

    ke_meta = (ke_metadata_index or {}).get(ke_id)
    ke_bio_level = ke_meta.get("biolevel") if ke_meta else None

    # GO hierarchy enrichment
    go_hier_entry = (go_hierarchy or {}).get(go_id)
    go_ic = round(go_hier_entry["ic_score"], 2) if go_hier_entry and go_hier_entry.get("ic_score") is not None else None
    go_depth = go_hier_entry.get("depth") if go_hier_entry else None

    go_bp_entry = (go_bp_metadata or {}).get(go_id)
    go_definition = go_bp_entry.get("definition") if go_bp_entry else None

    return {
        "uuid": row["uuid"],
        "ke_id": ke_id,
        "ke_name": row["ke_title"],
        "go_term_id": go_id,
        "go_term_name": row["go_name"],
        "go_namespace": row.get("go_namespace", "biological_process"),
        "confidence_level": row["confidence_level"],
        "go_direction": row.get("go_direction"),  # positive/negative/null
        "connection_type": row.get("connection_type"),
        "assessment_version": row.get("assessment_version", "v1"),
        "connection_score": row.get("connection_score"),   # null for v1 mappings
        "specificity_score": row.get("specificity_score"), # null for v1 mappings
        "evidence_score": row.get("evidence_score"),       # null for v1 mappings
        "ke_aop_context": ke_aop_context,
        "ke_bio_level": ke_bio_level,
        "go_definition": go_definition,
        "go_ic": go_ic,
        "go_depth": go_depth,
        "provenance": {
            "suggestion_score": row.get("suggestion_score"),
            "approved_by": row.get("approved_by_curator"),
            "approved_at": row.get("approved_at_curator"),
            "proposed_by": row.get("proposed_by"),
        },
    }


# CSV fieldnames — provenance is flattened (nested dicts don't serialize to CSV)
_MAPPING_CSV_FIELDS = [
    "uuid", "ke_id", "ke_name", "pathway_id", "pathway_title",
    "confidence_level", "suggestion_score", "approved_by", "approved_at", "proposed_by",
    "connection_type", "ke_aop_context", "ke_bio_level",
]
_GO_MAPPING_CSV_FIELDS = [
    "uuid", "ke_id", "ke_name", "go_term_id", "go_term_name", "go_namespace",
    "confidence_level", "go_direction", "suggestion_score", "approved_by", "approved_at", "proposed_by",
    "connection_type", "ke_aop_context", "ke_bio_level", "go_definition", "go_ic", "go_depth",
]


def _flatten_for_csv(obj):
    """Flatten provenance nested dict into the top-level object for CSV."""
    flat = dict(obj)
    prov = flat.pop("provenance", {})
    flat["suggestion_score"] = prov.get("suggestion_score")
    flat["approved_by"] = prov.get("approved_by")
    flat["approved_at"] = prov.get("approved_at")
    flat["proposed_by"] = prov.get("proposed_by")
    # Convert ke_aop_context array to semicolon-separated string for CSV
    aop_ctx = flat.get("ke_aop_context")
    flat["ke_aop_context"] = ";".join(aop_ctx) if aop_ctx else ""
    return flat


def _respond_collection(serialized_rows, pagination, csv_fields):
    """
    Return JSON or CSV based on Accept header or ?format=csv query param.
    JSON: {"data": [...], "pagination": {...}}
    CSV:  header row + data rows (provenance flattened)
    """
    format_param = request.args.get("format", "").lower()
    if format_param == "csv":
        use_csv = True
    else:
        best = request.accept_mimetypes.best_match(
            ["application/json", "text/csv"], default="application/json"
        )
        use_csv = best == "text/csv"

    if use_csv:
        flat_rows = [_flatten_for_csv(r) for r in serialized_rows]
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=csv_fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(flat_rows)
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=ke_wp_mappings.csv"
        return response
    return jsonify({"data": serialized_rows, "pagination": pagination})


def _resolve_aop_ke_ids(aop_id):
    """
    Resolve aop_id to a list of KE ID strings using AOP-Wiki SPARQL + cache.

    Returns:
        list of ke_id strings — may be empty if AOP has no KEs in SPARQL
    Raises:
        ValueError — if SPARQL is unavailable or aop_id is not found
    """
    aop_label = f"AOP {aop_id}" if aop_id.isdigit() else aop_id
    cache_key = f"aop_kes_{aop_label}"
    query_hash = hashlib.md5(cache_key.encode()).hexdigest()
    endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"

    cached = cache_model.get_cached_response(endpoint, query_hash)
    if cached:
        results = json.loads(cached)
        return [item["KElabel"] for item in results]

    sparql_query = f"""
    PREFIX aopo: <http://aopkb.org/aop_ontology#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX nci: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT DISTINCT ?ke ?keId ?keTitle ?biolevel ?kePage
    WHERE {{
        ?aop a aopo:AdverseOutcomePathway ;
             rdfs:label "{aop_label}" ;
             aopo:has_key_event ?ke .
        ?ke a aopo:KeyEvent ;
            rdfs:label ?keId ;
            dc:title ?keTitle ;
            foaf:page ?kePage .
        OPTIONAL {{ ?ke nci:C25664 ?biolevel }}
    }}
    ORDER BY ?keId
    """

    try:
        response = requests_lib.post(
            endpoint,
            data={"query": sparql_query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
    except requests_lib.exceptions.Timeout:
        raise ValueError("AOP-Wiki SPARQL timed out")
    except Exception as exc:
        raise ValueError(f"AOP-Wiki SPARQL unavailable: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(f"AOP-Wiki SPARQL returned {response.status_code}")

    data = response.json()
    if "results" not in data or "bindings" not in data["results"]:
        raise ValueError("Invalid SPARQL response format")

    results = [
        {
            "KElabel": binding.get("keId", {}).get("value", ""),
            "KEtitle": binding.get("keTitle", {}).get("value", ""),
        }
        for binding in data["results"]["bindings"]
        if "keId" in binding and "keTitle" in binding
    ]

    # Cache for 24 hours (same TTL as api_bp.get_aop_kes)
    cache_model.cache_response(endpoint, query_hash, json.dumps(results), 24)
    return [item["KElabel"] for item in results]


# ---------------------------------------------------------------------------
# Routes: KE-WP Mappings
# ---------------------------------------------------------------------------

@v1_api_bp.route("/mappings", methods=["GET"])
def list_mappings():
    """
    GET /api/v1/mappings

    Query params (all optional, combinable):
      ke_id            — filter by KE ID (comma-separated for multiple)
      pathway_id       — filter by WikiPathways ID (comma-separated)
      confidence_level — filter by confidence level (High/Medium/Low, case-insensitive)
      aop_id           — filter to KEs belonging to this AOP (numeric or "AOP N")
      page             — page number (default 1)
      per_page         — results per page (default 50, max 200)

    Accept header:
      application/json (default) — returns {"data": [...], "pagination": {...}}
      text/csv                   — returns CSV with flattened provenance
    """
    page, per_page = _parse_pagination_params()

    # Filter params
    ke_id_raw = request.args.get("ke_id")
    pathway_id_raw = request.args.get("pathway_id")
    confidence_level = request.args.get("confidence_level")
    aop_id = request.args.get("aop_id")

    # Comma-separated multi-value support — use first value if single given
    ke_id = ke_id_raw.split(",")[0].strip() if ke_id_raw else None
    pathway_id = pathway_id_raw.split(",")[0].strip() if pathway_id_raw else None

    ke_ids = None  # None means "no AOP filter"; [] means "AOP valid but no KEs"
    if aop_id:
        try:
            ke_ids = _resolve_aop_ke_ids(aop_id.strip())
        except ValueError as exc:
            logger.warning("AOP resolution failed for '%s': %s", sanitize_log(aop_id), exc)
            return jsonify({"error": f"AOP ID not found or SPARQL unavailable: {aop_id}"}), 400

    try:
        rows, total = mapping_model.get_mappings_paginated(
            page=page,
            per_page=per_page,
            ke_id=ke_id,
            pathway_id=pathway_id,
            confidence_level=confidence_level,
            ke_ids=ke_ids,
        )
    except Exception as exc:
        logger.error("Error in list_mappings: %s", exc)
        return jsonify({"error": "Failed to retrieve mappings"}), 500

    serialized = [_serialize_mapping(r) for r in rows]
    base_url = request.url_root.rstrip("/") + "/api/v1/mappings"
    extra_params = {}
    if ke_id_raw:
        extra_params["ke_id"] = ke_id_raw
    if pathway_id_raw:
        extra_params["pathway_id"] = pathway_id_raw
    if confidence_level:
        extra_params["confidence_level"] = confidence_level
    if aop_id:
        extra_params["aop_id"] = aop_id
    pagination = _make_pagination(page, per_page, total, base_url, extra_params)

    return _respond_collection(serialized, pagination, _MAPPING_CSV_FIELDS)


@v1_api_bp.route("/mappings/<uuid>", methods=["GET"])
def get_mapping(uuid):
    """
    GET /api/v1/mappings/<uuid>

    Returns a single mapping by its stable UUID.
    Returns 404 if the UUID does not exist.
    """
    try:
        row = mapping_model.get_mapping_by_uuid(uuid)
    except Exception as exc:
        logger.error("Error in get_mapping uuid=%s: %s", sanitize_log(uuid), exc)
        return jsonify({"error": "Failed to retrieve mapping"}), 500

    if row is None:
        return jsonify({"error": f"Mapping not found: {uuid}"}), 404

    return jsonify({"data": _serialize_mapping(row)})


# ---------------------------------------------------------------------------
# Routes: KE-GO Mappings
# ---------------------------------------------------------------------------

@v1_api_bp.route("/go-mappings", methods=["GET"])
def list_go_mappings():
    """
    GET /api/v1/go-mappings

    Query params (all optional, combinable):
      ke_id            — filter by KE ID (comma-separated for multiple)
      go_term_id       — filter by GO term ID (comma-separated)
      confidence_level — filter by confidence level (High/Medium/Low, case-insensitive)
      direction        — filter by GO direction: "positive" or "negative"
      page             — page number (default 1)
      per_page         — results per page (default 50, max 200)

    Accept header:
      application/json (default) — returns {"data": [...], "pagination": {...}}
      text/csv                   — returns CSV with flattened provenance
    """
    page, per_page = _parse_pagination_params()

    ke_id_raw = request.args.get("ke_id")
    go_term_id_raw = request.args.get("go_term_id")
    confidence_level = request.args.get("confidence_level")
    direction = request.args.get("direction")

    if direction is not None and direction not in ("positive", "negative"):
        return jsonify({"error": "Invalid direction value. Must be 'positive' or 'negative'"}), 400

    ke_id = ke_id_raw.split(",")[0].strip() if ke_id_raw else None
    go_term_id = go_term_id_raw.split(",")[0].strip() if go_term_id_raw else None

    try:
        rows, total = go_mapping_model.get_go_mappings_paginated(
            page=page,
            per_page=per_page,
            ke_id=ke_id,
            go_term_id=go_term_id,
            confidence_level=confidence_level,
            direction=direction,
        )
    except Exception as exc:
        logger.error("Error in list_go_mappings: %s", exc)
        return jsonify({"error": "Failed to retrieve GO mappings"}), 500

    serialized = [_serialize_go_mapping(r) for r in rows]
    base_url = request.url_root.rstrip("/") + "/api/v1/go-mappings"
    extra_params = {}
    if ke_id_raw:
        extra_params["ke_id"] = ke_id_raw
    if go_term_id_raw:
        extra_params["go_term_id"] = go_term_id_raw
    if confidence_level:
        extra_params["confidence_level"] = confidence_level
    if direction:
        extra_params["direction"] = direction
    pagination = _make_pagination(page, per_page, total, base_url, extra_params)

    return _respond_collection(serialized, pagination, _GO_MAPPING_CSV_FIELDS)


@v1_api_bp.route("/go-mappings/<uuid>", methods=["GET"])
def get_go_mapping(uuid):
    """
    GET /api/v1/go-mappings/<uuid>

    Returns a single KE-GO mapping by its stable UUID.
    Returns 404 if the UUID does not exist.
    """
    try:
        row = go_mapping_model.get_go_mapping_by_uuid(uuid)
    except Exception as exc:
        logger.error("Error in get_go_mapping uuid=%s: %s", sanitize_log(uuid), exc)
        return jsonify({"error": "Failed to retrieve GO mapping"}), 500

    if row is None:
        return jsonify({"error": f"GO mapping not found: {uuid}"}), 404

    return jsonify({"data": _serialize_go_mapping(row)})
