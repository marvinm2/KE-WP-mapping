"""
Main Blueprint
Handles core application routes and page rendering
"""
from flask import Blueprint, render_template, send_file, session
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
    """Download dataset as CSV file"""
    try:
        if not os.path.exists("dataset.csv"):
            logger.error("Dataset file not found for download")
            return render_template('error.html', error="Dataset not available for download"), 404
        return send_file("dataset.csv", as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        return render_template('error.html', error="Failed to download dataset"), 500

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