"""
Main Blueprint
Handles core application routes and page rendering
"""
import logging
import os

from flask import Blueprint, make_response, render_template, send_file, session, request, jsonify

from models import MappingModel
from monitoring import monitor_performance

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)

# Global model instances (will be set by app initialization)
mapping_model = None
export_manager = None
metadata_manager = None


def set_models(mapping, export_mgr=None, metadata_mgr=None):
    """Set the model instances"""
    global mapping_model, export_manager, metadata_manager
    mapping_model = mapping
    export_manager = export_mgr
    metadata_manager = metadata_mgr


def is_admin(username: str = None) -> bool:
    """
    Check if a user has admin privileges

    Args:
        username: Username to check (defaults to current session user)

    Returns:
        True if user is admin, False otherwise
    """
    if not username:
        username = session.get("user", {}).get("username")

    admin_users = os.getenv("ADMIN_USERS", "").split(",")
    admin_users = [user.strip() for user in admin_users if user.strip()]

    return username in admin_users


@main_bp.route("/")
@monitor_performance
def index():
    """Main application page"""
    return render_template("index.html")


@main_bp.route("/explore")
@monitor_performance
def explore():
    """Dataset exploration page"""
    try:
        user_info = session.get("user", {})
        data = mapping_model.get_all_mappings()
        return render_template("explore.html", dataset=data, user_info=user_info)
    except Exception as e:
        logger.error(f"Error loading dataset: {str(e)}")
        return render_template(
            "explore.html", dataset=[], user_info={}, error="Failed to load dataset"
        )


@main_bp.route("/download")
def download():
    """Generate and download comprehensive dataset with metadata"""
    try:
        import csv
        import io
        from datetime import datetime

        # Get all mappings from database
        mappings = mapping_model.get_all_mappings()

        if not mappings:
            logger.warning("No mappings found for download")
            return (
                render_template("error.html", error="No data available for download"),
                404,
            )

        # Create CSV content in memory
        output = io.StringIO()

        # Generate statistics
        confidence_stats = {}
        connection_stats = {}
        contributor_stats = {}

        for mapping in mappings:
            conf = mapping.get("confidence_level", "unknown")
            conn = mapping.get("connection_type", "unknown")
            contrib = mapping.get("created_by", "anonymous")

            confidence_stats[conf] = confidence_stats.get(conf, 0) + 1
            connection_stats[conn] = connection_stats.get(conn, 0) + 1
            contributor_stats[contrib] = contributor_stats.get(contrib, 0) + 1

        # Add comprehensive metadata header
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        output.write(f"# KE-WP Mapping Dataset Export\n")
        output.write(f"# Generated: {current_time}\n")
        output.write(f"# Total mappings: {len(mappings)}\n")
        output.write(
            f"# Unique Key Events: {len(set(m.get('ke_id') for m in mappings if m.get('ke_id')))}\n"
        )
        output.write(
            f"# Unique WikiPathways: {len(set(m.get('wp_id') for m in mappings if m.get('wp_id')))}\n"
        )
        output.write(f"# Contributors: {len(contributor_stats)}\n")
        output.write(f"#\n")
        output.write(f"# Confidence distribution:\n")
        for conf, count in sorted(confidence_stats.items()):
            output.write(f"#   {conf}: {count} ({count/len(mappings)*100:.1f}%)\n")
        output.write(f"#\n")
        output.write(f"# Connection type distribution:\n")
        for conn, count in sorted(connection_stats.items()):
            output.write(f"#   {conn}: {count} ({count/len(mappings)*100:.1f}%)\n")
        output.write(f"#\n")
        output.write(
            f"# Data sources: AOP-Wiki SPARQL (https://aopwiki.rdf.bigcat-bioinformatics.org/sparql), WikiPathways SPARQL (https://sparql.wikipathways.org/sparql)\n"
        )
        output.write(
            f"# Description: Curated mappings between Key Events and WikiPathways with confidence assessments\n"
        )
        output.write(f"# License: CC0 - Public Domain\n")
        output.write(f"# Repository: https://github.com/marvinm2/KE-WP-mapping\n")
        output.write(f"# Contact: Generated from KE-WP Mapping Service\n")
        output.write(f"#\n")
        output.write(f"# Column descriptions:\n")
        output.write(f"# - id: Unique identifier for the mapping\n")
        output.write(f"# - ke_id: Key Event identifier from AOP-Wiki\n")
        output.write(f"# - ke_title: Full title of the Key Event\n")
        output.write(f"# - wp_id: WikiPathways identifier\n")
        output.write(f"# - wp_title: Full title of the WikiPathways pathway\n")
        output.write(
            f"# - connection_type: Type of relationship (causative, responsive, other, undefined)\n"
        )
        output.write(f"# - confidence_level: Expert assessment (high, medium, low)\n")
        output.write(f"# - created_by: GitHub username of contributor\n")
        output.write(f"# - created_at: Timestamp when mapping was created\n")
        output.write(f"# - updated_at: Timestamp when mapping was last updated\n")
        output.write(
            f"# - updated_by: GitHub username of last updater (if different from creator)\n"
        )
        output.write(f"#\n")

        # Define CSV columns
        fieldnames = [
            "id",
            "ke_id",
            "ke_title",
            "wp_id",
            "wp_title",
            "connection_type",
            "confidence_level",
            "created_by",
            "created_at",
            "updated_at",
            "updated_by",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        # Write mapping data
        for mapping in mappings:
            # Convert database row to dictionary and handle None values
            row_data = {
                "id": mapping.get("id"),
                "ke_id": mapping.get("ke_id"),
                "ke_title": mapping.get("ke_title", ""),
                "wp_id": mapping.get("wp_id"),
                "wp_title": mapping.get("wp_title", ""),
                "connection_type": mapping.get("connection_type"),
                "confidence_level": mapping.get("confidence_level"),
                "created_by": mapping.get("created_by", ""),
                "created_at": mapping.get("created_at", ""),
                "updated_at": mapping.get("updated_at", ""),
                "updated_by": mapping.get("updated_by", mapping.get("created_by", "")),
            }
            writer.writerow(row_data)

        # Prepare file for download
        output.seek(0)
        csv_content = output.getvalue()
        output.close()

        # Create response with proper headers
        response = make_response(csv_content)
        response.headers["Content-Type"] = "text/csv"
        response.headers[
            "Content-Disposition"
        ] = f'attachment; filename=ke_wp_mappings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        logger.info(f"Dataset downloaded: {len(mappings)} mappings exported")
        return response

    except Exception as e:
        logger.error(f"Error generating dataset download: {str(e)}")
        return (
            render_template("error.html", error="Failed to generate dataset download"),
            500,
        )


@main_bp.route("/ke-details")
def ke_details():
    """Key Event details page"""
    return render_template("ke-details.html")


@main_bp.route("/pw-details")
def pw_details():
    """Pathway details page"""
    return render_template("pw-details.html")


@main_bp.route("/confidence_assessment")
@monitor_performance
def confidence_assessment():
    """Confidence assessment page"""
    return render_template("confidence-assessment.html")


@main_bp.route("/aop_network")
@monitor_performance
def aop_network():
    """AOP Network Visualization page"""
    return render_template("aop_network.html")


# ========== Enhanced Export Routes ==========

@main_bp.route("/export/<format_name>")
@monitor_performance
def export_dataset(format_name):
    """Export dataset in specified format"""
    if not export_manager:
        return jsonify({"error": "Export functionality not available"}), 500
    
    try:
        # Validate format
        available_formats = export_manager.get_available_formats()
        if format_name not in available_formats:
            return jsonify({
                "error": f"Unsupported format: {format_name}",
                "available_formats": available_formats
            }), 400
        
        # Get export options from query parameters
        include_metadata = request.args.get('metadata', 'true').lower() == 'true'
        include_statistics = request.args.get('statistics', 'true').lower() == 'true'
        include_provenance = request.args.get('provenance', 'true').lower() == 'true'
        compression = request.args.get('compression', 'snappy')
        
        # Export data
        if format_name == 'json':
            export_data = export_manager.export('json', 
                include_metadata=include_metadata, 
                include_provenance=include_provenance
            )
        elif format_name == 'jsonld':
            export_data = export_manager.export('jsonld', 
                include_metadata=include_metadata
            )
        elif format_name in ['excel', 'xlsx']:
            export_data = export_manager.export('excel',
                include_statistics=include_statistics,
                include_metadata=include_metadata
            )
        elif format_name == 'parquet':
            export_data = export_manager.export('parquet',
                include_metadata_columns=include_metadata,
                compression=compression
            )
        else:
            export_data = export_manager.export(format_name)
        
        # Create response
        response = make_response(export_data)
        response.headers["Content-Type"] = export_manager.get_content_type(format_name)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = export_manager.get_file_extension(format_name)
        filename = f"ke_wp_mappings_{timestamp}.{extension}"
        
        if format_name in ['excel', 'parquet']:
            response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
        
        # Add custom headers
        response.headers["X-Dataset-Version"] = metadata_manager.metadata.get("version", "1.0.0") if metadata_manager else "1.0.0"
        response.headers["X-Export-Format"] = format_name
        response.headers["X-Export-Timestamp"] = datetime.now().isoformat()
        
        logger.info(f"Dataset exported in {format_name} format")
        return response
        
    except ImportError as e:
        return jsonify({
            "error": f"Required dependencies not installed for {format_name} export",
            "details": str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error exporting dataset in {format_name} format: {e}")
        return jsonify({"error": "Export failed", "details": str(e)}), 500


@main_bp.route("/export/formats")
def list_export_formats():
    """List available export formats"""
    if not export_manager:
        return jsonify({"error": "Export functionality not available"}), 500
    
    formats_info = {
        "available_formats": export_manager.get_available_formats(),
        "format_details": {
            "csv": {
                "description": "Comma-separated values with comprehensive metadata header",
                "content_type": "text/csv",
                "use_cases": ["Spreadsheet analysis", "Basic data processing"]
            },
            "json": {
                "description": "Comprehensive JSON with schema, statistics, and provenance",
                "content_type": "application/json", 
                "use_cases": ["Web APIs", "Data interchange", "Programmatic access"]
            },
            "jsonld": {
                "description": "JSON-LD format for semantic web applications",
                "content_type": "application/ld+json",
                "use_cases": ["Semantic web", "Linked data", "Knowledge graphs"]
            },
            "rdf": {
                "description": "RDF/XML format with biological ontologies",
                "content_type": "application/rdf+xml",
                "use_cases": ["Ontology integration", "Semantic reasoning"]
            },
            "turtle": {
                "description": "Turtle format for RDF data",
                "content_type": "text/turtle",
                "use_cases": ["Triple stores", "SPARQL queries"]
            },
            "excel": {
                "description": "Excel workbook with multiple sheets and data dictionary",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "use_cases": ["Data analysis", "Reporting", "Manual review"]
            },
            "parquet": {
                "description": "Columnar format optimized for analytics",
                "content_type": "application/octet-stream",
                "use_cases": ["Big data analytics", "Machine learning", "Data science"]
            }
        }
    }
    
    return jsonify(formats_info)


@main_bp.route("/dataset/metadata")
def dataset_metadata():
    """Get comprehensive dataset metadata"""
    if not metadata_manager:
        return jsonify({"error": "Metadata functionality not available"}), 500
    
    try:
        metadata = metadata_manager.get_current_metadata()
        return jsonify(metadata)
    except Exception as e:
        logger.error(f"Error retrieving dataset metadata: {e}")
        return jsonify({"error": "Failed to retrieve metadata", "details": str(e)}), 500


@main_bp.route("/dataset/versions")
def dataset_versions():
    """Get dataset version history"""
    if not metadata_manager:
        return jsonify({"error": "Metadata functionality not available"}), 500
    
    try:
        versions = metadata_manager.get_versions()
        return jsonify({"versions": versions})
    except Exception as e:
        logger.error(f"Error retrieving dataset versions: {e}")
        return jsonify({"error": "Failed to retrieve versions", "details": str(e)}), 500


@main_bp.route("/dataset/citation")
def dataset_citation():
    """Generate dataset citation in various formats"""
    if not metadata_manager:
        return jsonify({"error": "Metadata functionality not available"}), 500
    
    citation_format = request.args.get('format', 'apa').lower()
    
    try:
        citation = metadata_manager.generate_citation(citation_format)
        
        response_data = {
            "format": citation_format,
            "citation": citation,
            "available_formats": ["apa", "bibtex"]
        }
        
        if citation_format == "bibtex":
            response = make_response(citation)
            response.headers["Content-Type"] = "application/x-bibtex"
            response.headers["Content-Disposition"] = 'inline; filename="ke_wp_dataset.bib"'
            return response
        else:
            return jsonify(response_data)
            
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating citation: {e}")
        return jsonify({"error": "Failed to generate citation", "details": str(e)}), 500


@main_bp.route("/dataset/datacite")
def datacite_metadata():
    """Get DataCite XML metadata"""
    if not metadata_manager:
        return jsonify({"error": "Metadata functionality not available"}), 500
    
    try:
        datacite_xml = metadata_manager.export_datacite_xml()
        
        response = make_response(datacite_xml)
        response.headers["Content-Type"] = "application/xml"
        response.headers["Content-Disposition"] = 'inline; filename="datacite_metadata.xml"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating DataCite metadata: {e}")
        return jsonify({"error": "Failed to generate DataCite metadata", "details": str(e)}), 500
