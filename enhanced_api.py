"""
Enhanced RESTful API with full CRUD operations, pagination, and OpenAPI documentation
"""
import logging
from datetime import datetime
from typing import Dict, List

from flask import Blueprint, jsonify, request
from marshmallow import Schema, fields, validate

from models import MappingModel
from monitoring import monitor_performance
from rate_limiter import general_rate_limit
from schemas import MappingSchema, validate_request_data
from text_utils import sanitize_log

logger = logging.getLogger(__name__)

enhanced_api_bp = Blueprint("enhanced_api", __name__, url_prefix="/api/v1")

# Global model instances
mapping_model = None
export_manager = None
metadata_manager = None


def set_models(mapping, export_mgr=None, metadata_mgr=None):
    """Set the model instances"""
    global mapping_model, export_manager, metadata_manager
    mapping_model = mapping
    export_manager = export_mgr
    metadata_manager = metadata_mgr


class PaginationSchema(Schema):
    """Schema for pagination parameters"""
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = fields.String(missing="created_at")
    sort_order = fields.String(missing="desc", validate=validate.OneOf(["asc", "desc"]))


class FilterSchema(Schema):
    """Schema for filtering parameters"""
    ke_id = fields.String()
    wp_id = fields.String()
    connection_type = fields.String(validate=validate.OneOf(["causative", "responsive", "other", "undefined"]))
    confidence_level = fields.String(validate=validate.OneOf(["low", "medium", "high"]))
    created_by = fields.String()
    created_after = fields.DateTime()
    created_before = fields.DateTime()
    search = fields.String()  # Full-text search


def paginate_results(results: List[Dict], page: int, per_page: int) -> Dict:
    """Paginate results and return pagination metadata"""
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_results = results[start:end]
    
    return {
        "data": paginated_results,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
            "has_next": end < total,
            "has_prev": page > 1,
            "next_page": page + 1 if end < total else None,
            "prev_page": page - 1 if page > 1 else None
        }
    }


def filter_mappings(mappings: List[Dict], filters: Dict) -> List[Dict]:
    """Apply filters to mappings"""
    filtered = mappings
    
    if filters.get("ke_id"):
        filtered = [m for m in filtered if m.get("ke_id") == filters["ke_id"]]
    
    if filters.get("wp_id"):
        filtered = [m for m in filtered if m.get("wp_id") == filters["wp_id"]]
    
    if filters.get("connection_type"):
        filtered = [m for m in filtered if m.get("connection_type") == filters["connection_type"]]
    
    if filters.get("confidence_level"):
        filtered = [m for m in filtered if m.get("confidence_level") == filters["confidence_level"]]
    
    if filters.get("created_by"):
        filtered = [m for m in filtered if m.get("created_by") == filters["created_by"]]
    
    if filters.get("created_after"):
        after_date = filters["created_after"]
        filtered = [m for m in filtered if m.get("created_at") and m["created_at"] >= after_date.isoformat()]
    
    if filters.get("created_before"):
        before_date = filters["created_before"]
        filtered = [m for m in filtered if m.get("created_at") and m["created_at"] <= before_date.isoformat()]
    
    if filters.get("search"):
        search_term = filters["search"].lower()
        filtered = [m for m in filtered if 
                   search_term in (m.get("ke_title", "") or "").lower() or
                   search_term in (m.get("wp_title", "") or "").lower() or
                   search_term in (m.get("ke_id", "") or "").lower() or
                   search_term in (m.get("wp_id", "") or "").lower()]
    
    return filtered


def sort_mappings(mappings: List[Dict], sort_by: str, sort_order: str) -> List[Dict]:
    """Sort mappings by specified field"""
    reverse = sort_order == "desc"
    
    try:
        return sorted(mappings, key=lambda x: x.get(sort_by, ""), reverse=reverse)
    except (TypeError, KeyError):
        # Fallback to ID sorting if sort field is invalid
        return sorted(mappings, key=lambda x: x.get("id", 0), reverse=reverse)


# ========== CRUD Endpoints ==========

@enhanced_api_bp.route("/mappings", methods=["GET"])
@general_rate_limit
@monitor_performance
def list_mappings():
    """Get paginated list of mappings with filtering and sorting"""
    try:
        # Validate pagination parameters
        pagination_schema = PaginationSchema()
        pagination_data = pagination_schema.load(request.args)
        
        # Validate filter parameters
        filter_schema = FilterSchema()
        filter_data = filter_schema.load(request.args)
        
        # Get all mappings
        all_mappings = mapping_model.get_all_mappings()
        
        # Apply filters
        filtered_mappings = filter_mappings(all_mappings, filter_data)
        
        # Apply sorting
        sorted_mappings = sort_mappings(
            filtered_mappings,
            pagination_data["sort_by"],
            pagination_data["sort_order"]
        )
        
        # Apply pagination
        result = paginate_results(
            sorted_mappings,
            pagination_data["page"],
            pagination_data["per_page"]
        )
        
        # Add metadata
        result["meta"] = {
            "filters_applied": {k: v for k, v in filter_data.items() if v is not None},
            "sort": {
                "field": pagination_data["sort_by"],
                "order": pagination_data["sort_order"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error listing mappings: %s", e)
        return jsonify({"error": "Failed to retrieve mappings", "details": "Internal error"}), 500


@enhanced_api_bp.route("/mappings/<int:mapping_id>", methods=["GET"])
@general_rate_limit
@monitor_performance
def get_mapping(mapping_id):
    """Get specific mapping by ID"""
    try:
        # Get all mappings and find the specific one
        all_mappings = mapping_model.get_all_mappings()
        mapping = next((m for m in all_mappings if m["id"] == mapping_id), None)
        
        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404
        
        # Add related information
        result = {
            "data": mapping,
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "links": {
                    "aop_wiki": f"https://aopwiki.org/events/{mapping['ke_id'].replace('KE ', '')}",
                    "wikipathways": f"https://www.wikipathways.org/pathways/{mapping['wp_id']}.html"
                }
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error retrieving mapping %s: %s", mapping_id, sanitize_log(str(e)))
        return jsonify({"error": "Failed to retrieve mapping", "details": "Internal error"}), 500


@enhanced_api_bp.route("/mappings", methods=["POST"])
@general_rate_limit
@monitor_performance
def create_mapping():
    """Create new mapping"""
    try:
        # Validate request data
        is_valid, validated_data, errors = validate_request_data(MappingSchema, request.json)
        
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        
        # Check for existing mapping
        existing = mapping_model.check_mapping_exists(
            validated_data["ke_id"],
            validated_data["wp_id"]
        )
        
        if existing.get("pair_exists"):
            return jsonify({"error": "Mapping already exists", "details": existing}), 409
        
        # Create mapping
        mapping_id = mapping_model.create_mapping(
            ke_id=validated_data["ke_id"],
            ke_title=validated_data["ke_title"],
            wp_id=validated_data["wp_id"],
            wp_title=validated_data["wp_title"],
            connection_type=validated_data["connection_type"],
            confidence_level=validated_data["confidence_level"],
            created_by=request.json.get("created_by", "api_user")
        )
        
        if not mapping_id:
            return jsonify({"error": "Failed to create mapping"}), 500
        
        # Return created mapping
        result = {
            "data": {
                "id": mapping_id,
                **validated_data,
                "created_by": request.json.get("created_by", "api_user"),
                "created_at": datetime.now().isoformat()
            },
            "meta": {
                "message": "Mapping created successfully",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error("Error creating mapping: %s", e)
        return jsonify({"error": "Failed to create mapping", "details": "Internal error"}), 500


@enhanced_api_bp.route("/mappings/<int:mapping_id>", methods=["PUT", "PATCH"])
@general_rate_limit
@monitor_performance
def update_mapping(mapping_id):
    """Update existing mapping"""
    try:
        # Check if mapping exists
        all_mappings = mapping_model.get_all_mappings()
        existing_mapping = next((m for m in all_mappings if m["id"] == mapping_id), None)
        
        if not existing_mapping:
            return jsonify({"error": "Mapping not found"}), 404
        
        # For PATCH, allow partial updates; for PUT, require full data
        if request.method == "PATCH":
            # Validate only provided fields
            update_data = {}
            if "connection_type" in request.json:
                if request.json["connection_type"] not in ["causative", "responsive", "other", "undefined"]:
                    return jsonify({"error": "Invalid connection_type"}), 400
                update_data["connection_type"] = request.json["connection_type"]
            
            if "confidence_level" in request.json:
                if request.json["confidence_level"] not in ["low", "medium", "high"]:
                    return jsonify({"error": "Invalid confidence_level"}), 400
                update_data["confidence_level"] = request.json["confidence_level"]
                
        else:  # PUT - require full data
            is_valid, validated_data, errors = validate_request_data(MappingSchema, request.json)
            
            if not is_valid:
                return jsonify({"error": "Validation failed", "details": errors}), 400
            
            update_data = {
                "connection_type": validated_data["connection_type"],
                "confidence_level": validated_data["confidence_level"]
            }
        
        if not update_data:
            return jsonify({"error": "No valid update fields provided"}), 400
        
        # Update mapping
        success = mapping_model.update_mapping(
            mapping_id=mapping_id,
            connection_type=update_data.get("connection_type"),
            confidence_level=update_data.get("confidence_level"),
            updated_by=request.json.get("updated_by", "api_user")
        )
        
        if not success:
            return jsonify({"error": "Failed to update mapping"}), 500
        
        # Return updated mapping data
        updated_mapping = {**existing_mapping, **update_data}
        updated_mapping["updated_at"] = datetime.now().isoformat()
        updated_mapping["updated_by"] = request.json.get("updated_by", "api_user")
        
        result = {
            "data": updated_mapping,
            "meta": {
                "message": "Mapping updated successfully",
                "timestamp": datetime.now().isoformat(),
                "changes": list(update_data.keys())
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error updating mapping %s: %s", mapping_id, sanitize_log(str(e)))
        return jsonify({"error": "Failed to update mapping", "details": "Internal error"}), 500


@enhanced_api_bp.route("/mappings/<int:mapping_id>", methods=["DELETE"])
@general_rate_limit
@monitor_performance
def delete_mapping(mapping_id):
    """Delete mapping"""
    try:
        # Check if mapping exists
        all_mappings = mapping_model.get_all_mappings()
        existing_mapping = next((m for m in all_mappings if m["id"] == mapping_id), None)
        
        if not existing_mapping:
            return jsonify({"error": "Mapping not found"}), 404
        
        # Delete mapping
        success = mapping_model.delete_mapping(
            mapping_id=mapping_id,
            deleted_by=request.json.get("deleted_by", "api_user") if request.json else "api_user"
        )
        
        if not success:
            return jsonify({"error": "Failed to delete mapping"}), 500
        
        result = {
            "meta": {
                "message": "Mapping deleted successfully",
                "timestamp": datetime.now().isoformat(),
                "deleted_mapping": existing_mapping
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error deleting mapping %s: %s", mapping_id, sanitize_log(str(e)))
        return jsonify({"error": "Failed to delete mapping", "details": "Internal error"}), 500


# ========== Bulk Operations ==========

@enhanced_api_bp.route("/mappings/bulk", methods=["POST"])
@general_rate_limit
@monitor_performance
def bulk_operations():
    """Perform bulk operations on mappings"""
    try:
        if not request.json or "operation" not in request.json:
            return jsonify({"error": "Operation type required"}), 400
        
        operation = request.json["operation"]
        
        if operation == "create":
            return bulk_create_mappings()
        elif operation == "update":
            return bulk_update_mappings()
        elif operation == "delete":
            return bulk_delete_mappings()
        else:
            return jsonify({"error": f"Unsupported bulk operation: {operation}"}), 400
            
    except Exception as e:
        logger.error("Error in bulk operations: %s", e)
        return jsonify({"error": "Bulk operation failed", "details": "Internal error"}), 500


def bulk_create_mappings():
    """Create multiple mappings in batch"""
    if "mappings" not in request.json:
        return jsonify({"error": "Mappings array required"}), 400
    
    mappings_data = request.json["mappings"]
    results = {"created": [], "failed": []}
    
    for i, mapping_data in enumerate(mappings_data):
        try:
            # Validate each mapping
            is_valid, validated_data, errors = validate_request_data(MappingSchema, mapping_data)
            
            if not is_valid:
                results["failed"].append({
                    "index": i,
                    "data": mapping_data,
                    "error": "Validation failed",
                    "details": errors
                })
                continue
            
            # Check for existing mapping
            existing = mapping_model.check_mapping_exists(
                validated_data["ke_id"],
                validated_data["wp_id"]
            )
            
            if existing.get("pair_exists"):
                results["failed"].append({
                    "index": i,
                    "data": mapping_data,
                    "error": "Mapping already exists"
                })
                continue
            
            # Create mapping
            mapping_id = mapping_model.create_mapping(
                ke_id=validated_data["ke_id"],
                ke_title=validated_data["ke_title"],
                wp_id=validated_data["wp_id"],
                wp_title=validated_data["wp_title"],
                connection_type=validated_data["connection_type"],
                confidence_level=validated_data["confidence_level"],
                created_by=mapping_data.get("created_by", "api_bulk")
            )
            
            if mapping_id:
                results["created"].append({
                    "id": mapping_id,
                    **validated_data,
                    "created_by": mapping_data.get("created_by", "api_bulk")
                })
            else:
                results["failed"].append({
                    "index": i,
                    "data": mapping_data,
                    "error": "Failed to create mapping"
                })
                
        except Exception as e:
            logger.error("Error in bulk create for index %d: %s", i, e)
            results["failed"].append({
                "index": i,
                "data": mapping_data,
                "error": "Internal error"
            })
    
    response = {
        "data": results,
        "meta": {
            "total_processed": len(mappings_data),
            "created": len(results["created"]),
            "failed": len(results["failed"]),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    status_code = 200 if results["created"] else 400
    return jsonify(response), status_code


def bulk_update_mappings():
    """Bulk update mappings (not yet implemented)"""
    return jsonify({"error": "Bulk update not yet implemented"}), 501


def bulk_delete_mappings():
    """Bulk delete mappings (not yet implemented)"""
    return jsonify({"error": "Bulk delete not yet implemented"}), 501


# ========== Statistics and Analytics ==========

@enhanced_api_bp.route("/mappings/stats", methods=["GET"])
@general_rate_limit
@monitor_performance
def mapping_statistics():
    """Get comprehensive mapping statistics"""
    try:
        all_mappings = mapping_model.get_all_mappings()
        
        # Basic statistics
        total = len(all_mappings)
        
        # Confidence distribution
        confidence_dist = {}
        for mapping in all_mappings:
            conf = mapping.get("confidence_level", "unknown")
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
        
        # Connection type distribution
        connection_dist = {}
        for mapping in all_mappings:
            conn = mapping.get("connection_type", "unknown")
            connection_dist[conn] = connection_dist.get(conn, 0) + 1
        
        # Contributor statistics
        contributors = {}
        for mapping in all_mappings:
            contrib = mapping.get("created_by", "anonymous")
            contributors[contrib] = contributors.get(contrib, 0) + 1
        
        # Temporal distribution
        temporal_dist = {}
        for mapping in all_mappings:
            if mapping.get("created_at"):
                try:
                    date = mapping["created_at"][:7]  # YYYY-MM format
                    temporal_dist[date] = temporal_dist.get(date, 0) + 1
                except (TypeError, IndexError):
                    continue
        
        # Unique entities
        unique_kes = len(set(m.get("ke_id") for m in all_mappings if m.get("ke_id")))
        unique_wps = len(set(m.get("wp_id") for m in all_mappings if m.get("wp_id")))
        
        result = {
            "data": {
                "summary": {
                    "total_mappings": total,
                    "unique_key_events": unique_kes,
                    "unique_pathways": unique_wps,
                    "contributors": len(contributors)
                },
                "distributions": {
                    "confidence_levels": confidence_dist,
                    "connection_types": connection_dist,
                    "temporal": dict(sorted(temporal_dist.items())),
                    "contributors": dict(sorted(contributors.items(), key=lambda x: x[1], reverse=True))
                }
            },
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "generated_by": "KE-WP Mapping API v1"
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error generating statistics: %s", e)
        return jsonify({"error": "Failed to generate statistics", "details": "Internal error"}), 500


# ========== API Documentation ==========

@enhanced_api_bp.route("/", methods=["GET"])
def api_documentation():
    """API documentation and available endpoints"""
    endpoints = {
        "version": "1.0.0",
        "description": "Enhanced RESTful API for KE-WP Mapping Dataset",
        "base_url": "/api/v1",
        "authentication": "Optional (GitHub OAuth for write operations)",
        "rate_limits": "General: 1000/hour, Submission: 100/hour",
        "endpoints": {
            "GET /mappings": {
                "description": "List mappings with pagination, filtering, and sorting",
                "parameters": {
                    "page": "Page number (default: 1)",
                    "per_page": "Items per page (1-100, default: 20)",
                    "sort_by": "Sort field (default: created_at)",
                    "sort_order": "asc or desc (default: desc)",
                    "ke_id": "Filter by Key Event ID",
                    "wp_id": "Filter by WikiPathway ID",
                    "connection_type": "Filter by connection type",
                    "confidence_level": "Filter by confidence level",
                    "created_by": "Filter by creator",
                    "search": "Full-text search in titles and IDs"
                }
            },
            "GET /mappings/{id}": {
                "description": "Get specific mapping by ID"
            },
            "POST /mappings": {
                "description": "Create new mapping",
                "content_type": "application/json",
                "required_fields": ["ke_id", "ke_title", "wp_id", "wp_title", "connection_type", "confidence_level"]
            },
            "PUT /mappings/{id}": {
                "description": "Update mapping (full update)",
                "content_type": "application/json"
            },
            "PATCH /mappings/{id}": {
                "description": "Update mapping (partial update)",
                "content_type": "application/json"
            },
            "DELETE /mappings/{id}": {
                "description": "Delete mapping"
            },
            "POST /mappings/bulk": {
                "description": "Bulk operations (create, update, delete)",
                "content_type": "application/json"
            },
            "GET /mappings/stats": {
                "description": "Get mapping statistics and analytics"
            }
        },
        "schemas": {
            "mapping": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Unique identifier"},
                    "ke_id": {"type": "string", "pattern": "^KE\\s+\\d+$"},
                    "ke_title": {"type": "string", "maxLength": 500},
                    "wp_id": {"type": "string", "pattern": "^WP\\d+$"},
                    "wp_title": {"type": "string", "maxLength": 500},
                    "connection_type": {"type": "string", "enum": ["causative", "responsive", "other", "undefined"]},
                    "confidence_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "created_by": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            }
        }
    }
    
    return jsonify(endpoints)