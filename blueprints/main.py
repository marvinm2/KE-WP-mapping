"""
Main Blueprint
Handles core application routes and page rendering
"""
from flask import Blueprint, render_template, send_file, session, make_response
import logging
import os

from models import MappingModel
from monitoring import monitor_performance

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# Global model instances (will be set by app initialization)
mapping_model = None

def set_models(mapping):
    """Set the model instances"""
    global mapping_model
    mapping_model = mapping

def is_admin(username: str = None) -> bool:
    """
    Check if a user has admin privileges
    
    Args:
        username: Username to check (defaults to current session user)
        
    Returns:
        True if user is admin, False otherwise
    """
    if not username:
        username = session.get('user', {}).get('username')
    
    admin_users = os.getenv('ADMIN_USERS', '').split(',')
    admin_users = [user.strip() for user in admin_users if user.strip()]
    
    return username in admin_users

@main_bp.route('/')
@monitor_performance
def index():
    """Main application page"""
    return render_template('index.html')

@main_bp.route('/explore')
@monitor_performance
def explore():
    """Dataset exploration page"""
    try:
        user_info = session.get('user', {})
        data = mapping_model.get_all_mappings()
        return render_template("explore.html", dataset=data, user_info=user_info)
    except Exception as e:
        logger.error(f"Error loading dataset: {str(e)}")
        return render_template("explore.html", dataset=[], user_info={}, error="Failed to load dataset")

@main_bp.route('/download')
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
            return render_template('error.html', error="No data available for download"), 404
        
        # Create CSV content in memory
        output = io.StringIO()
        
        # Generate statistics
        confidence_stats = {}
        connection_stats = {}
        contributor_stats = {}
        
        for mapping in mappings:
            conf = mapping.get('confidence_level', 'unknown')
            conn = mapping.get('connection_type', 'unknown')
            contrib = mapping.get('created_by', 'anonymous')
            
            confidence_stats[conf] = confidence_stats.get(conf, 0) + 1
            connection_stats[conn] = connection_stats.get(conn, 0) + 1
            contributor_stats[contrib] = contributor_stats.get(contrib, 0) + 1
        
        # Add comprehensive metadata header
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        output.write(f"# KE-WP Mapping Dataset Export\n")
        output.write(f"# Generated: {current_time}\n")
        output.write(f"# Total mappings: {len(mappings)}\n")
        output.write(f"# Unique Key Events: {len(set(m.get('ke_id') for m in mappings if m.get('ke_id')))}\n")
        output.write(f"# Unique WikiPathways: {len(set(m.get('wp_id') for m in mappings if m.get('wp_id')))}\n")
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
        output.write(f"# Data sources: AOP-Wiki SPARQL (https://aopwiki.rdf.bigcat-bioinformatics.org/sparql), WikiPathways SPARQL (https://sparql.wikipathways.org/sparql)\n")
        output.write(f"# Description: Curated mappings between Key Events and WikiPathways with confidence assessments\n")
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
        output.write(f"# - connection_type: Type of relationship (causative, responsive, other, undefined)\n")
        output.write(f"# - confidence_level: Expert assessment (high, medium, low)\n")
        output.write(f"# - created_by: GitHub username of contributor\n")
        output.write(f"# - created_at: Timestamp when mapping was created\n")
        output.write(f"# - updated_at: Timestamp when mapping was last updated\n")
        output.write(f"# - updated_by: GitHub username of last updater (if different from creator)\n")
        output.write(f"#\n")
        
        # Define CSV columns
        fieldnames = [
            'id', 'ke_id', 'ke_title', 'wp_id', 'wp_title', 
            'connection_type', 'confidence_level', 'created_by', 
            'created_at', 'updated_at', 'updated_by'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write mapping data
        for mapping in mappings:
            # Convert database row to dictionary and handle None values
            row_data = {
                'id': mapping.get('id'),
                'ke_id': mapping.get('ke_id'),
                'ke_title': mapping.get('ke_title', ''),
                'wp_id': mapping.get('wp_id'),
                'wp_title': mapping.get('wp_title', ''),
                'connection_type': mapping.get('connection_type'),
                'confidence_level': mapping.get('confidence_level'),
                'created_by': mapping.get('created_by', ''),
                'created_at': mapping.get('created_at', ''),
                'updated_at': mapping.get('updated_at', ''),
                'updated_by': mapping.get('updated_by', mapping.get('created_by', ''))
            }
            writer.writerow(row_data)
        
        # Prepare file for download
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        # Create response with proper headers
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=ke_wp_mappings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        logger.info(f"Dataset downloaded: {len(mappings)} mappings exported")
        return response
        
    except Exception as e:
        logger.error(f"Error generating dataset download: {str(e)}")
        return render_template('error.html', error="Failed to generate dataset download"), 500

@main_bp.route('/ke-details')
def ke_details():
    """Key Event details page"""
    return render_template('ke-details.html')

@main_bp.route('/pw-details')
def pw_details():
    """Pathway details page"""
    return render_template('pw-details.html')

@main_bp.route('/confidence_assessment')
@monitor_performance
def confidence_assessment():
    """Confidence assessment page"""
    return render_template('confidence-assessment.html')