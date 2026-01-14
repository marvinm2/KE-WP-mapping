"""
API Blueprint
Handles all API endpoints for data submission and retrieval
"""
import hashlib
import json
import logging
import time
from datetime import datetime
from functools import wraps

import requests
from flask import Blueprint, jsonify, request, session

from models import CacheModel, MappingModel, ProposalModel
from monitoring import monitor_performance
from rate_limiter import general_rate_limit, sparql_rate_limit, submission_rate_limit
from schemas import (
    CheckEntrySchema,
    MappingSchema,
    ProposalSchema,
    SecurityValidation,
    validate_request_data,
)
from config_loader import ConfigLoader

logger = logging.getLogger(__name__)

# Module-level cache for scoring config
_config_cache = None
_config_cache_time = None
_config_cache_ttl = 300  # 5 minutes

api_bp = Blueprint("api", __name__)

# Global model instances (will be set by app initialization)
mapping_model = None
proposal_model = None
cache_model = None
pathway_suggestion_service = None


def set_models(mapping, proposal, cache, suggestion_service=None):
    """Set the model instances"""
    global mapping_model, proposal_model, cache_model, pathway_suggestion_service
    mapping_model = mapping
    proposal_model = proposal
    cache_model = cache
    pathway_suggestion_service = suggestion_service


def login_required(f):
    """Decorator to require login for protected routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


@api_bp.route("/check", methods=["POST"])
@general_rate_limit
def check_entry():
    """Check if the KE ID or the KE-WP pair already exist in the dataset."""
    try:
        # Extract only the required fields for validation
        check_data = {
            "ke_id": request.form.get("ke_id"),
            "wp_id": request.form.get("wp_id"),
        }

        # Validate input data
        is_valid, validated_data, errors = validate_request_data(
            CheckEntrySchema, check_data
        )

        if not is_valid:
            logger.warning(f"Invalid check entry request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        ke_id = validated_data["ke_id"]
        wp_id = validated_data["wp_id"]

        result = mapping_model.check_mapping_exists(ke_id, wp_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error checking entry: {str(e)}")
        return jsonify({"error": "Failed to check entry"}), 500


@api_bp.route("/submit", methods=["POST"])
@submission_rate_limit
@login_required
def submit():
    """Add a new KE-WP mapping entry to the dataset."""
    try:
        # Extract only the required fields for validation (exclude CSRF token)
        submit_data = {
            "ke_id": request.form.get("ke_id"),
            "ke_title": request.form.get("ke_title"),
            "wp_id": request.form.get("wp_id"),
            "wp_title": request.form.get("wp_title"),
            "connection_type": request.form.get("connection_type"),
            "confidence_level": request.form.get("confidence_level"),
        }

        # Validate input data
        is_valid, validated_data, errors = validate_request_data(
            MappingSchema, submit_data
        )

        if not is_valid:
            logger.warning(f"Invalid submit request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Sanitize string inputs
        ke_id = SecurityValidation.sanitize_string(validated_data["ke_id"])
        ke_title = SecurityValidation.sanitize_string(validated_data["ke_title"])
        wp_id = SecurityValidation.sanitize_string(validated_data["wp_id"])
        wp_title = SecurityValidation.sanitize_string(validated_data["wp_title"])
        connection_type = validated_data["connection_type"]
        confidence_level = validated_data["confidence_level"]

        # Get current user
        created_by = session.get("user", {}).get("username", "anonymous")

        # Additional validation for GitHub username if available
        if created_by != "anonymous" and not SecurityValidation.validate_username(
            created_by
        ):
            logger.error(f"Invalid username format: {created_by}")
            return jsonify({"error": "Authentication error"}), 401

        # Create mapping
        mapping_id = mapping_model.create_mapping(
            ke_id=ke_id,
            ke_title=ke_title,
            wp_id=wp_id,
            wp_title=wp_title,
            connection_type=connection_type,
            confidence_level=confidence_level,
            created_by=created_by,
        )

        if mapping_id:
            logger.info(f"New mapping created: {ke_id} -> {wp_id} by {created_by}")
            return jsonify({"message": "Entry added successfully."}), 200
        else:
            return (
                jsonify({"error": "The KE-WP pair already exists in the dataset."}),
                400,
            )
    except Exception as e:
        logger.error(f"Error adding entry: {str(e)}")
        return jsonify({"error": "Failed to add entry"}), 500


@api_bp.route("/get_ke_options", methods=["GET"])
@sparql_rate_limit
def get_ke_options():
    """Fetch Key Event options from SPARQL endpoint"""
    try:
        sparql_query = """
        PREFIX aopo: <http://aopkb.org/aop_ontology#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX nci: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>

        SELECT ?KEtitle ?KElabel ?KEpage ?KEdescription ?biolevel
        WHERE {
          ?KE a aopo:KeyEvent ; 
              dc:title ?KEtitle ; 
              rdfs:label ?KElabel; 
              foaf:page ?KEpage .
          OPTIONAL { ?KE dc:description ?KEdescription }
          OPTIONAL { ?KE nci:C25664 ?biolevel }
        }
        """
        endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"

        # Check cache first
        query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
        cached_response = cache_model.get_cached_response(endpoint, query_hash)

        if cached_response:
            logger.info("Serving KE options from cache")
            return jsonify(json.loads(cached_response)), 200

        response = requests.post(
            endpoint,
            data={"query": sparql_query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            if "results" not in data or "bindings" not in data["results"]:
                logger.error("Invalid SPARQL response format")
                return jsonify({"error": "Invalid response from KE service"}), 500

            results = [
                {
                    "KEtitle": binding.get("KEtitle", {}).get("value", ""),
                    "KElabel": binding.get("KElabel", {}).get("value", ""),
                    "KEpage": binding.get("KEpage", {}).get("value", ""),
                    "KEdescription": binding.get("KEdescription", {}).get("value", ""),
                    "biolevel": binding.get("biolevel", {}).get("value", ""),
                }
                for binding in data["results"]["bindings"]
                if all(key in binding for key in ["KEtitle", "KElabel", "KEpage"])
            ]

            # Cache the response
            cache_model.cache_response(endpoint, query_hash, json.dumps(results), 24)
            logger.info(f"Fetched and cached {len(results)} KE options")
            return jsonify(results), 200
        else:
            logger.error(
                f"SPARQL Query Failed: {response.status_code} - {response.text}"
            )
            return jsonify({"error": "Failed to fetch KE options"}), 500
    except requests.exceptions.Timeout:
        logger.error("SPARQL request timeout")
        return jsonify({"error": "Service timeout - please try again"}), 503
    except Exception as e:
        logger.error(f"Error fetching KE options: {str(e)}")
        return jsonify({"error": "Failed to fetch KE options"}), 500


@api_bp.route("/get_pathway_options", methods=["GET"])
@sparql_rate_limit
def get_pathway_options():
    """Fetch pathway options from the SPARQL endpoint."""
    try:
        sparql_query = """
        PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?pathwayID ?pathwayTitle ?pathwayLink ?pathwayDescription
        WHERE {
            ?pathwayRev a wp:Pathway ; 
                        dc:title ?pathwayTitle ; 
                        dc:identifier ?pathwayLink ; 
                        dcterms:identifier ?pathwayID ;
                        wp:organismName "Homo sapiens" .
            OPTIONAL { ?pathwayRev dcterms:description ?pathwayDescription }
        }
        """
        endpoint = "https://sparql.wikipathways.org/sparql"

        # Check cache first
        query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
        cached_response = cache_model.get_cached_response(endpoint, query_hash)

        if cached_response:
            logger.info("Serving pathway options from cache")
            return jsonify(json.loads(cached_response)), 200

        response = requests.post(
            endpoint,
            data={"query": sparql_query},
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            if "results" not in data or "bindings" not in data["results"]:
                logger.error("Invalid SPARQL response format")
                return jsonify({"error": "Invalid response from pathway service"}), 500

            results = [
                {
                    "pathwayID": binding.get("pathwayID", {}).get("value", ""),
                    "pathwayTitle": binding.get("pathwayTitle", {}).get("value", ""),
                    "pathwayLink": binding.get("pathwayLink", {}).get("value", ""),
                    "pathwayDescription": binding.get("pathwayDescription", {}).get(
                        "value", ""
                    ),
                }
                for binding in data["results"]["bindings"]
                if all(
                    key in binding
                    for key in ["pathwayID", "pathwayTitle", "pathwayLink"]
                )
            ]

            # Cache the response
            cache_model.cache_response(endpoint, query_hash, json.dumps(results), 24)
            logger.info(f"Fetched and cached {len(results)} pathway options")
            return jsonify(results), 200
        else:
            logger.error(
                f"SPARQL Pathway Query Failed: {response.status_code} - {response.text}"
            )
            return jsonify({"error": "Failed to fetch pathway options"}), 500
    except requests.exceptions.Timeout:
        logger.error("SPARQL pathway request timeout")
        return jsonify({"error": "Service timeout - please try again"}), 503
    except Exception as e:
        logger.error(f"Error fetching pathway options: {str(e)}")
        return jsonify({"error": "Failed to fetch pathway options"}), 500


@api_bp.route("/get_data_versions", methods=["GET"])
@sparql_rate_limit
def get_data_versions():
    """Fetch version information from AOP-Wiki and WikiPathways SPARQL endpoints."""
    try:
        versions = {}
        
        # Get AOP-Wiki version info
        try:
            aop_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            
            SELECT DISTINCT ?version ?date ?comment
            WHERE {
                ?dataset a <http://rdfs.org/ns/void#Dataset> .
                OPTIONAL { ?dataset dcterms:hasVersion ?version }
                OPTIONAL { ?dataset dcterms:created ?date }
                OPTIONAL { ?dataset rdfs:comment ?comment }
            } LIMIT 1
            """
            
            aop_endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"
            aop_response = requests.post(
                aop_endpoint,
                data={"query": aop_query, "format": "json"},
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            if aop_response.status_code == 200:
                aop_data = aop_response.json()
                if aop_data.get("results", {}).get("bindings"):
                    result = aop_data["results"]["bindings"][0]
                    versions["aop_wiki"] = {
                        "source": "AOP-Wiki RDF",
                        "version": result.get("version", {}).get("value", "Unknown"),
                        "date": result.get("date", {}).get("value", "Unknown"),
                        "comment": result.get("comment", {}).get("value", ""),
                        "endpoint": aop_endpoint
                    }
                else:
                    versions["aop_wiki"] = {
                        "source": "AOP-Wiki RDF",
                        "version": "Available",
                        "date": "Unknown",
                        "comment": "SPARQL endpoint accessible",
                        "endpoint": aop_endpoint
                    }
                    
        except Exception as e:
            logger.warning(f"Could not fetch AOP-Wiki version: {e}")
            versions["aop_wiki"] = {
                "source": "AOP-Wiki RDF",
                "version": "Unknown",
                "date": "Unknown",
                "comment": f"Error: {str(e)}",
                "endpoint": "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"
            }
        
        # Get WikiPathways version info
        try:
            wp_query = """
            PREFIX void: <http://rdfs.org/ns/void#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT DISTINCT ?version ?date ?title
            WHERE {
                ?dataset a void:Dataset .
                OPTIONAL { ?dataset dcterms:hasVersion ?version }
                OPTIONAL { ?dataset dcterms:created ?date }
                OPTIONAL { ?dataset dcterms:title ?title }
            } LIMIT 1
            """
            
            wp_endpoint = "https://sparql.wikipathways.org/sparql"
            wp_response = requests.post(
                wp_endpoint,
                data={"query": wp_query, "format": "json"},
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            if wp_response.status_code == 200:
                wp_data = wp_response.json()
                if wp_data.get("results", {}).get("bindings"):
                    result = wp_data["results"]["bindings"][0]
                    versions["wikipathways"] = {
                        "source": "WikiPathways",
                        "version": result.get("version", {}).get("value", "Current"),
                        "date": result.get("date", {}).get("value", "Unknown"),
                        "comment": result.get("title", {}).get("value", ""),
                        "endpoint": wp_endpoint
                    }
                else:
                    versions["wikipathways"] = {
                        "source": "WikiPathways",
                        "version": "Current",
                        "date": "Unknown",
                        "comment": "SPARQL endpoint accessible",
                        "endpoint": wp_endpoint
                    }
                    
        except Exception as e:
            logger.warning(f"Could not fetch WikiPathways version: {e}")
            versions["wikipathways"] = {
                "source": "WikiPathways",
                "version": "Unknown",
                "date": "Unknown", 
                "comment": f"Error: {str(e)}",
                "endpoint": "https://sparql.wikipathways.org/sparql"
            }
        
        return jsonify(versions), 200
        
    except Exception as e:
        logger.error(f"Error fetching data versions: {e}")
        return jsonify({"error": "Failed to load data version information"}), 500


@api_bp.route("/submit_proposal", methods=["POST"])
@login_required
@submission_rate_limit
def submit_proposal():
    """
    Save user proposals to database for admin review

    Handles proposal submission from the explore page modal form.
    Proposals are stored in the database with status 'pending' for admin review.

    Returns:
        JSON response with success/error message
    """
    try:
        # Extract only the required fields for validation (exclude CSRF token)
        proposal_data = {
            "entry": request.form.get("entry"),
            "userName": request.form.get("userName"),
            "userEmail": request.form.get("userEmail"),
            "userAffiliation": request.form.get("userAffiliation"),
            "deleteEntry": request.form.get("deleteEntry", ""),
            "changeConfidence": request.form.get("changeConfidence", ""),
            "changeType": request.form.get("changeType", ""),
        }

        # Debug logging
        logger.info(f"Proposal submission data: {proposal_data}")

        # Validate input data
        is_valid, validated_data, errors = validate_request_data(
            ProposalSchema, proposal_data
        )

        if not is_valid:
            logger.warning(f"Invalid proposal request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Sanitize and extract validated data
        entry_data = validated_data["entry"]
        user_name = SecurityValidation.sanitize_string(validated_data["userName"])
        user_email = validated_data["userEmail"]
        user_affiliation = SecurityValidation.sanitize_string(
            validated_data["userAffiliation"]
        )

        # Extract proposed changes
        proposed_delete = validated_data["deleteEntry"] == "on"
        proposed_confidence = validated_data.get("changeConfidence") or None
        proposed_connection_type = validated_data.get("changeType") or None

        # Additional email domain validation
        if not SecurityValidation.validate_email_domain(user_email):
            return jsonify({"error": "Invalid email domain."}), 400

        # Parse entry data to extract KE and WP IDs
        try:
            import json

            # Handle double-serialized JSON
            if entry_data.startswith('"') and entry_data.endswith('"'):
                entry_data = json.loads(entry_data)  # First deserialization
            entry_dict = json.loads(
                entry_data.replace("'", '"')
            )  # Second deserialization with quote fix
            ke_id = entry_dict.get("ke_id") or entry_dict.get("KE_ID")
            wp_id = entry_dict.get("wp_id") or entry_dict.get("WP_ID")

            if not ke_id or not wp_id:
                return jsonify({"error": "Invalid entry data format."}), 400

        except (json.JSONDecodeError, AttributeError):
            return jsonify({"error": "Could not parse entry data."}), 400

        # Find the mapping ID
        mapping_id = proposal_model.find_mapping_by_details(ke_id, wp_id)
        if not mapping_id:
            return jsonify({"error": "Original mapping not found."}), 404

        # Get current user
        github_username = session.get("user", {}).get("username", "unknown")

        # Create proposal in database
        proposal_id = proposal_model.create_proposal(
            mapping_id=mapping_id,
            user_name=user_name,
            user_email=user_email,
            user_affiliation=user_affiliation,
            github_username=github_username,
            proposed_delete=proposed_delete,
            proposed_confidence=proposed_confidence if proposed_confidence else None,
            proposed_connection_type=proposed_connection_type
            if proposed_connection_type
            else None,
        )

        if proposal_id:
            logger.info(
                f"Created proposal {proposal_id} by user {github_username} for mapping {mapping_id}"
            )
            return (
                jsonify(
                    {
                        "message": "Proposal submitted successfully and is pending admin review.",
                        "proposal_id": proposal_id,
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "Failed to create proposal"}), 500

    except Exception as e:
        logger.error(f"Error saving proposal: {str(e)}")
        return jsonify({"error": "Failed to save proposal"}), 500


@api_bp.route("/suggest_pathways/<ke_id>", methods=["GET"])
@sparql_rate_limit
def suggest_pathways(ke_id):
    """
    Get pathway suggestions for a specific Key Event using multiple scoring methods

    Args:
        ke_id: Key Event ID from URL parameter

    Query Parameters:
        ke_title: Key Event title for text-based matching
        bio_level: Biological level of the KE (Molecular, Cellular, etc.)
        limit: Maximum number of suggestions (default 10)

    Returns:
        JSON response with:
        - gene_based_suggestions: Pathways matched by gene overlap
        - text_based_suggestions: Pathways matched by text similarity
        - embedding_based_suggestions: Pathways matched by BioBERT semantic similarity (if enabled)
        - combined_suggestions: Unified list with hybrid scores and transparency
        - genes_found: Number of genes associated with the KE
        - gene_list: List of HGNC gene symbols
        - total_suggestions: Total number of combined suggestions
    """
    try:
        if not pathway_suggestion_service:
            logger.error("Pathway suggestion service not available")
            return jsonify({"error": "Suggestion service unavailable"}), 503
            
        # Get parameters
        ke_title = request.args.get('ke_title', '')
        bio_level = request.args.get('bio_level', '')
        limit = request.args.get('limit', 10, type=int)
        
        # Validate limit
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 10
            
        # Validate KE ID format
        if not ke_id or len(ke_id.strip()) == 0:
            return jsonify({"error": "Invalid Key Event ID"}), 400
            
        logger.info(f"Getting pathway suggestions for KE: {ke_id} (bio_level: {bio_level})")
        
        # Get suggestions from service with biological level context
        suggestions = pathway_suggestion_service.get_pathway_suggestions(
            ke_id, ke_title, bio_level, limit
        )
        
        if "error" in suggestions:
            logger.error(f"Suggestion service error: {suggestions['error']}")
            return jsonify(suggestions), 500
            
        # Add metadata
        suggestions["request_info"] = {
            "ke_id": ke_id,
            "ke_title": ke_title,
            "limit": limit,
            "timestamp": int(time.time())
        }
        
        logger.info(f"Returned {suggestions.get('total_suggestions', 0)} suggestions for KE {ke_id}")
        return jsonify(suggestions), 200
        
    except Exception as e:
        logger.error(f"Error getting pathway suggestions for {ke_id}: {str(e)}")
        return jsonify({"error": "Failed to get pathway suggestions"}), 500


@api_bp.route("/search_pathways", methods=["GET"])
@sparql_rate_limit 
def search_pathways():
    """
    Enhanced pathway search with fuzzy matching
    
    Query Parameters:
        q: Search query string (required)
        threshold: Minimum similarity threshold (0.0-1.0, default 0.4)
        limit: Maximum number of results (default 20)
        
    Returns:
        JSON response with matching pathways and relevance scores
    """
    try:
        if not pathway_suggestion_service:
            logger.error("Pathway suggestion service not available")
            return jsonify({"error": "Search service unavailable"}), 503
            
        # Get parameters
        query = request.args.get('q', '').strip()
        threshold = request.args.get('threshold', 0.4, type=float)
        limit = request.args.get('limit', 20, type=int)
        
        # Validate parameters
        if not query:
            return jsonify({"error": "Search query is required"}), 400
            
        if threshold < 0.1 or threshold > 1.0:
            threshold = 0.4
            
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 20
            
        logger.info(f"Searching pathways with query: '{query}', threshold: {threshold}")
        
        # Perform search
        results = pathway_suggestion_service.search_pathways(
            query, threshold, limit
        )
        
        response = {
            "query": query,
            "threshold": threshold,
            "limit": limit,
            "results": results,
            "total_results": len(results),
            "timestamp": int(time.time())
        }
        
        logger.info(f"Found {len(results)} pathways matching '{query}'")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error searching pathways: {str(e)}")
        return jsonify({"error": "Failed to search pathways"}), 500


@api_bp.route("/ke_genes/<ke_id>", methods=["GET"])
@sparql_rate_limit
def get_ke_genes(ke_id):
    """
    Get genes associated with a specific Key Event
    
    Args:
        ke_id: Key Event ID from URL parameter
        
    Returns:
        JSON response with list of HGNC gene symbols
    """
    try:
        if not pathway_suggestion_service:
            logger.error("Pathway suggestion service not available")
            return jsonify({"error": "Service unavailable"}), 503
            
        # Validate KE ID
        if not ke_id or len(ke_id.strip()) == 0:
            return jsonify({"error": "Invalid Key Event ID"}), 400
            
        logger.info(f"Getting genes for KE: {ke_id}")
        
        # Get genes from service
        genes = pathway_suggestion_service._get_genes_from_ke(ke_id)
        
        response = {
            "ke_id": ke_id,
            "genes": genes,
            "gene_count": len(genes),
            "timestamp": int(time.time())
        }
        
        logger.info(f"Found {len(genes)} genes for KE {ke_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting genes for KE {ke_id}: {str(e)}")
        return jsonify({"error": "Failed to get KE genes"}), 500


@api_bp.route("/api/scoring-config", methods=["GET"])
@general_rate_limit
def get_scoring_config():
    """
    Serve frontend scoring configuration

    Returns:
        JSON containing ke_pathway_assessment configuration section
        Cached for 5 minutes to reduce file I/O
    """
    global _config_cache, _config_cache_time

    try:
        now = time.time()

        # Check cache
        if _config_cache and _config_cache_time:
            if now - _config_cache_time < _config_cache_ttl:
                logger.debug("Serving scoring config from cache")
                return jsonify(_config_cache), 200

        # Load fresh config
        config = ConfigLoader.load_config()

        # Extract frontend-relevant section
        ke_assessment = config.ke_pathway_assessment

        response = {
            "version": config.metadata.get("version", "1.0.0"),
            "ke_pathway_assessment": {
                "evidence_quality": ke_assessment.evidence_quality,
                "pathway_specificity": ke_assessment.pathway_specificity,
                "ke_coverage": ke_assessment.ke_coverage,
                "biological_level": ke_assessment.biological_level,
                "confidence_thresholds": ke_assessment.confidence_thresholds,
                "max_scores": ke_assessment.max_scores,
                "connection_types": ke_assessment.connection_types,
            },
            "metadata": {
                "loaded_at": datetime.utcnow().isoformat() + "Z",
                "source": "scoring_config.yaml"
            }
        }

        # Update cache
        _config_cache = response
        _config_cache_time = now

        logger.info("Scoring configuration served to frontend")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error serving scoring config: {str(e)}")
        # Return defaults on error (200 with defaults, not 500)
        default_config = ConfigLoader.get_default_config()
        ke_assessment = default_config.ke_pathway_assessment

        return jsonify({
            "version": "1.0.0-default",
            "ke_pathway_assessment": {
                "evidence_quality": ke_assessment.evidence_quality,
                "pathway_specificity": ke_assessment.pathway_specificity,
                "ke_coverage": ke_assessment.ke_coverage,
                "biological_level": ke_assessment.biological_level,
                "confidence_thresholds": ke_assessment.confidence_thresholds,
                "max_scores": ke_assessment.max_scores,
                "connection_types": ke_assessment.connection_types,
            },
            "metadata": {
                "loaded_at": datetime.utcnow().isoformat() + "Z",
                "source": "default",
                "error": "Failed to load config file, using defaults"
            }
        }), 200