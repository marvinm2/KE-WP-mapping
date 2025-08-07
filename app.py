from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
import pandas as pd
import os
import requests
import sys
import hashlib
import json
import time
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from functools import wraps
import logging

# Import our models
from models import Database, MappingModel, ProposalModel, CacheModel
from rate_limiter import sparql_rate_limit, submission_rate_limit, general_rate_limit
from monitoring import metrics_collector, monitor_performance
from schemas import (
    MappingSchema, ProposalSchema, CheckEntrySchema, AdminNotesSchema,
    validate_request_data, SecurityValidation
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure secure sessions and security headers
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    WTF_CSRF_TIME_LIMIT=3600  # 1 hour CSRF token validity
)

# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning(f"CSRF error: {e.description} from {request.remote_addr}")
    if request.is_json or request.path.startswith('/api/') or request.path.startswith('/submit'):
        return jsonify({'error': 'CSRF token missing or invalid. Please refresh the page and try again.'}), 400
    return render_template('error.html', error='Security token expired. Please refresh the page and try again.'), 400

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' code.jquery.com cdn.datatables.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.datatables.net; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self' cdnjs.cloudflare.com"
    )
    return response

# Initialize database
db = Database()
mapping_model = MappingModel(db)
proposal_model = ProposalModel(db)
cache_model = CacheModel(db)

# Validate required environment variables
required_env_vars = ['GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET', 'FLASK_SECRET_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Configure GitHub OAuth
oauth = OAuth(app)
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return github.authorize_redirect(redirect_uri)


@app.route('/callback')
def authorize():
    try:
        token = github.authorize_access_token()
        user_info = github.get('user').json()
        user_email = github.get('user/emails').json()

        # Validate user_info
        if not user_info or 'login' not in user_info:
            logger.error("Failed to get user info from GitHub")
            return redirect(url_for('index'))

        # Store user info in session
        session['user'] = {
            'username': user_info['login'],
            'email': user_email[0]['email'] if user_email and len(user_email) > 0 else 'No public email',
        }
        logger.info(f"User {user_info['login']} logged in successfully")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to require admin privileges for protected routes
    
    Checks if the current user is in the admin whitelist defined in environment variables.
    Admin usernames should be comma-separated in ADMIN_USERS env var.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        
        current_user = session.get('user', {}).get('username')
        admin_users = os.getenv('ADMIN_USERS', '').split(',')
        admin_users = [user.strip() for user in admin_users if user.strip()]
        
        if current_user not in admin_users:
            logger.warning(f"User {current_user} attempted to access admin route")
            return jsonify({"error": "Admin access required"}), 403
            
        return f(*args, **kwargs)
    return decorated_function

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

# Make is_admin available in templates
@app.context_processor
def inject_admin_status():
    """Make admin status available to all templates"""
    return {
        'is_admin': is_admin(),
        'current_username': session.get('user', {}).get('username', '')
    }


# Run CSV migration on startup if needed
def migrate_csv_if_needed():
    if os.path.exists("dataset.csv"):
        logger.info("CSV file found, running migration to database")
        try:
            from migrate_csv_to_db import migrate_csv_to_db
            migrate_csv_to_db()
        except Exception as e:
            logger.error(f"CSV migration failed: {e}")

# Run migration check
migrate_csv_if_needed()

# Clean up expired cache on startup
cache_model.cleanup_expired_cache()

@app.route('/')
@monitor_performance
def index():
    return render_template('index.html')

@app.route('/explore')
@monitor_performance
def explore():
    try:
        user_info = session.get('user', {})
        data = mapping_model.get_all_mappings()
        return render_template("explore.html", dataset=data, user_info=user_info)
    except Exception as e:
        logger.error(f"Error loading dataset: {str(e)}")
        return render_template("explore.html", dataset=[], user_info={}, error="Failed to load dataset")




@app.route('/check', methods=['POST'])
@general_rate_limit
def check_entry():
    """Check if the KE ID or the KE-WP pair already exist in the dataset."""
    try:
        # Validate input data
        is_valid, validated_data, errors = validate_request_data(CheckEntrySchema, request.form)
        
        if not is_valid:
            logger.warning(f"Invalid check entry request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        ke_id = validated_data['ke_id']
        wp_id = validated_data['wp_id']

        result = mapping_model.check_mapping_exists(ke_id, wp_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error checking entry: {str(e)}")
        return jsonify({"error": "Failed to check entry"}), 500


@app.route('/submit', methods=['POST'])
@submission_rate_limit
def submit():
    """Add a new KE-WP mapping entry to the dataset."""
    try:
        # Validate input data
        is_valid, validated_data, errors = validate_request_data(MappingSchema, request.form)
        
        if not is_valid:
            logger.warning(f"Invalid submit request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Sanitize string inputs
        ke_id = SecurityValidation.sanitize_string(validated_data['ke_id'])
        ke_title = SecurityValidation.sanitize_string(validated_data['ke_title'])
        wp_id = SecurityValidation.sanitize_string(validated_data['wp_id'])
        wp_title = SecurityValidation.sanitize_string(validated_data['wp_title'])
        connection_type = validated_data['connection_type']
        confidence_level = validated_data['confidence_level']

        # Get current user
        created_by = session.get('user', {}).get('username', 'anonymous')
        
        # Additional validation for GitHub username if available
        if created_by != 'anonymous' and not SecurityValidation.validate_username(created_by):
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
            created_by=created_by
        )
        
        if mapping_id:
            logger.info(f"New mapping created: {ke_id} -> {wp_id} by {created_by}")
            return jsonify({"message": "Entry added successfully."}), 200
        else:
            return jsonify({"error": "The KE-WP pair already exists in the dataset."}), 400
    except Exception as e:
        logger.error(f"Error adding entry: {str(e)}")
        return jsonify({"error": "Failed to add entry"}), 500


@app.route('/get_ke_options', methods=['GET'])
@sparql_rate_limit
def get_ke_options():
    try:
        sparql_query = """
        PREFIX aopo: <http://aopkb.org/aop_ontology#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>

        SELECT ?KEtitle ?KElabel ?KEpage
        WHERE {
          ?KE a aopo:KeyEvent ; 
              dc:title ?KEtitle ; 
              rdfs:label ?KElabel; 
              foaf:page ?KEpage. 
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
            headers={"Accept": "application/json"},
            timeout=30
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
                    "KEpage": binding.get("KEpage", {}).get("value", "")
                }
                for binding in data["results"]["bindings"]
                if all(key in binding for key in ["KEtitle", "KElabel", "KEpage"])
            ]
            
            # Cache the response
            cache_model.cache_response(endpoint, query_hash, json.dumps(results), 24)
            logger.info(f"Fetched and cached {len(results)} KE options")
            return jsonify(results), 200
        else:
            logger.error(f"SPARQL Query Failed: {response.status_code} - {response.text}")
            return jsonify({"error": "Failed to fetch KE options"}), 500
    except requests.exceptions.Timeout:
        logger.error("SPARQL request timeout")
        return jsonify({"error": "Service timeout - please try again"}), 503
    except Exception as e:
        logger.error(f"Error fetching KE options: {str(e)}")
        return jsonify({"error": "Failed to fetch KE options"}), 500

@app.route('/get_pathway_options', methods=['GET'])
@sparql_rate_limit
def get_pathway_options():
    """Fetch pathway options from the SPARQL endpoint."""
    try:
        sparql_query = """
        PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?pathwayID ?pathwayTitle ?pathwayLink
        WHERE {
            ?pathwayRev a wp:Pathway ; 
                        dc:title ?pathwayTitle ; 
                        dc:identifier ?pathwayLink ; 
                        dcterms:identifier ?pathwayID ;
                        wp:organismName "Homo sapiens" .
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
            headers={"Accept": "application/json"},
            timeout=30
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
                    "pathwayLink": binding.get("pathwayLink", {}).get("value", "")
                }
                for binding in data["results"]["bindings"]
                if all(key in binding for key in ["pathwayID", "pathwayTitle", "pathwayLink"])
            ]
            
            # Cache the response
            cache_model.cache_response(endpoint, query_hash, json.dumps(results), 24)
            logger.info(f"Fetched and cached {len(results)} pathway options")
            return jsonify(results), 200
        else:
            logger.error(f"SPARQL Pathway Query Failed: {response.status_code} - {response.text}")
            return jsonify({"error": "Failed to fetch pathway options"}), 500
    except requests.exceptions.Timeout:
        logger.error("SPARQL pathway request timeout")
        return jsonify({"error": "Service timeout - please try again"}), 503
    except Exception as e:
        logger.error(f"Error fetching pathway options: {str(e)}")
        return jsonify({"error": "Failed to fetch pathway options"}), 500


@app.route('/download')
def download():
    try:
        if not os.path.exists("dataset.csv"):
            logger.error("Dataset file not found for download")
            return jsonify({"error": "Dataset not available"}), 404
        return send_file("dataset.csv", as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        return jsonify({"error": "Failed to download dataset"}), 500

@app.route('/ke-details')
def ke_details():
    return render_template('ke-details.html')

@app.route('/pw-details')
def pw_details():
    return render_template('pw-details.html')

@app.route('/submit_proposal', methods=['POST'])
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
        # Validate input data
        is_valid, validated_data, errors = validate_request_data(ProposalSchema, request.form)
        
        if not is_valid:
            logger.warning(f"Invalid proposal request: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Sanitize and extract validated data
        entry_data = validated_data['entry']
        user_name = SecurityValidation.sanitize_string(validated_data['userName'])
        user_email = validated_data['userEmail']
        user_affiliation = SecurityValidation.sanitize_string(validated_data['userAffiliation'])
        
        # Extract proposed changes
        proposed_delete = validated_data['deleteEntry'] == 'on'
        proposed_confidence = validated_data.get('changeConfidence') or None
        proposed_connection_type = validated_data.get('changeType') or None
        
        # Additional email domain validation
        if not SecurityValidation.validate_email_domain(user_email):
            return jsonify({"error": "Invalid email domain."}), 400
        
        # Parse entry data to extract KE and WP IDs
        try:
            import json
            entry_dict = json.loads(entry_data.replace("'", '"'))
            ke_id = entry_dict.get('ke_id') or entry_dict.get('KE_ID')
            wp_id = entry_dict.get('wp_id') or entry_dict.get('WP_ID')
            
            if not ke_id or not wp_id:
                return jsonify({"error": "Invalid entry data format."}), 400
                
        except (json.JSONDecodeError, AttributeError):
            return jsonify({"error": "Could not parse entry data."}), 400
        
        # Find the mapping ID
        mapping_id = proposal_model.find_mapping_by_details(ke_id, wp_id)
        if not mapping_id:
            return jsonify({"error": "Original mapping not found."}), 404
        
        # Get current user
        github_username = session.get('user', {}).get('username', 'unknown')
        
        # Create proposal in database
        proposal_id = proposal_model.create_proposal(
            mapping_id=mapping_id,
            user_name=user_name,
            user_email=user_email,
            user_affiliation=user_affiliation,
            github_username=github_username,
            proposed_delete=proposed_delete,
            proposed_confidence=proposed_confidence if proposed_confidence else None,
            proposed_connection_type=proposed_connection_type if proposed_connection_type else None
        )
        
        if proposal_id:
            logger.info(f"Created proposal {proposal_id} by user {github_username} for mapping {mapping_id}")
            return jsonify({
                "message": "Proposal submitted successfully and is pending admin review.",
                "proposal_id": proposal_id
            }), 200
        else:
            return jsonify({"error": "Failed to create proposal"}), 500
            
    except Exception as e:
        logger.error(f"Error saving proposal: {str(e)}")
        return jsonify({"error": "Failed to save proposal"}), 500

@app.route('/confidence_assessment')
@monitor_performance
def confidence_assessment():
    return render_template('confidence-assessment.html')

# Admin Routes
@app.route('/admin/proposals')
@admin_required
@monitor_performance
def admin_proposals():
    """
    Admin dashboard for managing proposals
    
    Displays all proposals with filtering and management capabilities.
    Only accessible to users listed in ADMIN_USERS environment variable.
    
    Returns:
        Rendered template with proposal data
    """
    try:
        # Get filter from query parameters
        status_filter = request.args.get('status', 'pending')
        if status_filter == 'all':
            status_filter = None
            
        # Get all proposals
        proposals = proposal_model.get_all_proposals(status=status_filter)
        
        # Add admin status to template context
        user_info = session.get('user', {})
        
        return render_template('admin_proposals.html', 
                             proposals=proposals, 
                             status_filter=status_filter or 'all',
                             user_info=user_info)
        
    except Exception as e:
        logger.error(f"Error loading admin proposals: {e}")
        return render_template('admin_proposals.html', 
                             proposals=[], 
                             error="Failed to load proposals",
                             user_info=session.get('user', {}))

@app.route('/admin/proposals/<int:proposal_id>')
@admin_required
@monitor_performance
def admin_proposal_detail(proposal_id: int):
    """
    View detailed information about a specific proposal
    
    Args:
        proposal_id: ID of the proposal to view
        
    Returns:
        JSON data with proposal details
    """
    try:
        proposal = proposal_model.get_proposal_by_id(proposal_id)
        if not proposal:
            return jsonify({"error": "Proposal not found"}), 404
        
        return jsonify(proposal)
    
    except Exception as e:
        logger.error(f"Error getting proposal {proposal_id}: {e}")
        return jsonify({"error": "Failed to load proposal"}), 500

@app.route('/admin/proposals/<int:proposal_id>/approve', methods=['POST'])
@admin_required
@submission_rate_limit
def approve_proposal(proposal_id: int):
    """
    Approve a proposal and apply the changes to the mapping
    
    Args:
        proposal_id: ID of the proposal to approve
        
    Returns:
        JSON response indicating success/failure
    """
    try:
        # Validate admin notes input
        is_valid, validated_data, errors = validate_request_data(AdminNotesSchema, request.form)
        
        if not is_valid:
            logger.warning(f"Invalid admin notes in approve: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400
        
        # Get sanitized admin notes
        admin_notes = SecurityValidation.sanitize_string(validated_data['admin_notes'], max_length=1000)
        admin_username = session.get('user', {}).get('username')
        
        # Validate admin username
        if not SecurityValidation.validate_username(admin_username):
            logger.error(f"Invalid admin username in approve: {admin_username}")
            return jsonify({"error": "Authentication error"}), 401
        
        # Get proposal details
        proposal = proposal_model.get_proposal_by_id(proposal_id)
        if not proposal:
            return jsonify({"error": "Proposal not found"}), 404
        
        if proposal['status'] != 'pending':
            return jsonify({"error": f"Proposal is already {proposal['status']}"}), 400
        
        # Apply the proposed changes
        success = True
        mapping_id = proposal['mapping_id']
        
        if proposal['proposed_delete']:
            # Delete the mapping
            success = mapping_model.delete_mapping(mapping_id, admin_username)
            action = "deleted"
        else:
            # Update the mapping
            success = mapping_model.update_mapping(
                mapping_id=mapping_id,
                connection_type=proposal['proposed_connection_type'],
                confidence_level=proposal['proposed_confidence'], 
                updated_by=admin_username
            )
            action = "updated"
        
        if success:
            # Update proposal status
            proposal_model.update_proposal_status(
                proposal_id=proposal_id,
                status='approved',
                admin_username=admin_username,
                admin_notes=admin_notes
            )
            
            logger.info(f"Proposal {proposal_id} approved by {admin_username}, mapping {action}")
            return jsonify({
                "message": f"Proposal approved successfully. Mapping {action}.",
                "action": action
            }), 200
        else:
            return jsonify({"error": f"Failed to {action.rstrip('d')} mapping"}), 500
            
    except Exception as e:
        logger.error(f"Error approving proposal {proposal_id}: {e}")
        return jsonify({"error": "Failed to approve proposal"}), 500

@app.route('/admin/proposals/<int:proposal_id>/reject', methods=['POST'])
@admin_required
@submission_rate_limit
def reject_proposal(proposal_id: int):
    """
    Reject a proposal with optional admin notes
    
    Args:
        proposal_id: ID of the proposal to reject
        
    Returns:
        JSON response indicating success/failure
    """
    try:
        # Validate admin notes input
        is_valid, validated_data, errors = validate_request_data(AdminNotesSchema, request.form)
        
        if not is_valid:
            logger.warning(f"Invalid admin notes in reject: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400
        
        # Get sanitized admin notes
        admin_notes = SecurityValidation.sanitize_string(validated_data['admin_notes'], max_length=1000)
        admin_username = session.get('user', {}).get('username')
        
        # Validate admin username
        if not SecurityValidation.validate_username(admin_username):
            logger.error(f"Invalid admin username in reject: {admin_username}")
            return jsonify({"error": "Authentication error"}), 401
        
        # Get proposal details
        proposal = proposal_model.get_proposal_by_id(proposal_id)
        if not proposal:
            return jsonify({"error": "Proposal not found"}), 404
        
        if proposal['status'] != 'pending':
            return jsonify({"error": f"Proposal is already {proposal['status']}"}), 400
        
        # Update proposal status to rejected
        success = proposal_model.update_proposal_status(
            proposal_id=proposal_id,
            status='rejected',
            admin_username=admin_username,
            admin_notes=admin_notes or "No reason provided"
        )
        
        if success:
            logger.info(f"Proposal {proposal_id} rejected by {admin_username}")
            return jsonify({"message": "Proposal rejected successfully."}), 200
        else:
            return jsonify({"error": "Failed to reject proposal"}), 500
            
    except Exception as e:
        logger.error(f"Error rejecting proposal {proposal_id}: {e}")
        return jsonify({"error": "Failed to reject proposal"}), 500

# Monitoring endpoints
@app.route('/metrics')
@general_rate_limit
def metrics():
    """Get system metrics (JSON API)"""
    return jsonify(metrics_collector.get_system_health())

@app.route('/metrics/<endpoint_name>')
@general_rate_limit
def endpoint_metrics(endpoint_name):
    """Get metrics for a specific endpoint"""
    hours = request.args.get('hours', 24, type=int)
    return jsonify(metrics_collector.get_endpoint_stats(endpoint_name, hours))

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": int(time.time()),
        "version": "1.0.0"
    })

if __name__ == '__main__':
    # Only run in debug mode if explicitly set in environment
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug_mode, host='127.0.0.1', port=port)
