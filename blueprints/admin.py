"""
Admin Blueprint
Handles administrative functions for proposal management
"""
import logging
import os
from functools import wraps

from flask import Blueprint, jsonify, render_template, request, session

from models import MappingModel, ProposalModel
from monitoring import monitor_performance
from rate_limiter import submission_rate_limit
from schemas import AdminNotesSchema, SecurityValidation, validate_request_data

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Global model instances (will be set by app initialization)
proposal_model = None
mapping_model = None


def set_models(proposal, mapping):
    """Set the model instances"""
    global proposal_model, mapping_model
    proposal_model = proposal
    mapping_model = mapping


def login_required(f):
    """Decorator to require login for protected routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
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
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401

        current_user = session.get("user", {}).get("username")
        admin_users = os.getenv("ADMIN_USERS", "").split(",")
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
        username = session.get("user", {}).get("username")

    admin_users = os.getenv("ADMIN_USERS", "").split(",")
    admin_users = [user.strip() for user in admin_users if user.strip()]

    return username in admin_users


@admin_bp.route("/proposals")
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
        status_filter = request.args.get("status", "pending")
        if status_filter == "all":
            status_filter = None

        # Get all proposals
        proposals = proposal_model.get_all_proposals(status=status_filter)

        # Add admin status to template context
        user_info = session.get("user", {})

        return render_template(
            "admin_proposals.html",
            proposals=proposals,
            status_filter=status_filter or "all",
            user_info=user_info,
        )

    except Exception as e:
        logger.error(f"Error loading admin proposals: {e}")
        return render_template(
            "admin_proposals.html",
            proposals=[],
            error="Failed to load proposals",
            user_info=session.get("user", {}),
        )


@admin_bp.route("/proposals/<int:proposal_id>")
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


@admin_bp.route("/proposals/<int:proposal_id>/approve", methods=["POST"])
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
        # Extract only the required fields for validation (exclude CSRF token)
        admin_data = {"admin_notes": request.form.get("admin_notes", "")}

        # Debug logging
        logger.info(f"Admin approve request data: {admin_data}")

        # Validate admin notes input
        is_valid, validated_data, errors = validate_request_data(
            AdminNotesSchema, admin_data
        )

        if not is_valid:
            logger.warning(f"Invalid admin notes in approve: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Get sanitized admin notes
        admin_notes = SecurityValidation.sanitize_string(
            validated_data["admin_notes"], max_length=1000
        )
        admin_username = session.get("user", {}).get("username")

        # Validate admin username
        if not SecurityValidation.validate_username(admin_username):
            logger.error(f"Invalid admin username in approve: {admin_username}")
            return jsonify({"error": "Authentication error"}), 401

        # Get proposal details
        proposal = proposal_model.get_proposal_by_id(proposal_id)
        if not proposal:
            return jsonify({"error": "Proposal not found"}), 404

        if proposal["status"] != "pending":
            return jsonify({"error": f"Proposal is already {proposal['status']}"}), 400

        # Apply the proposed changes
        success = True
        mapping_id = proposal["mapping_id"]

        if proposal["proposed_delete"]:
            # Delete the mapping
            success = mapping_model.delete_mapping(mapping_id, admin_username)
            action = "deleted"
        else:
            # Update the mapping
            success = mapping_model.update_mapping(
                mapping_id=mapping_id,
                connection_type=proposal["proposed_connection_type"],
                confidence_level=proposal["proposed_confidence"],
                updated_by=admin_username,
            )
            action = "updated"

        if success:
            # Update proposal status
            proposal_model.update_proposal_status(
                proposal_id=proposal_id,
                status="approved",
                admin_username=admin_username,
                admin_notes=admin_notes,
            )

            logger.info(
                f"Proposal {proposal_id} approved by {admin_username}, mapping {action}"
            )
            return (
                jsonify(
                    {
                        "message": f"Proposal approved successfully. Mapping {action}.",
                        "action": action,
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": f"Failed to {action.rstrip('d')} mapping"}), 500

    except Exception as e:
        logger.error(f"Error approving proposal {proposal_id}: {e}")
        return jsonify({"error": "Failed to approve proposal"}), 500


@admin_bp.route("/proposals/<int:proposal_id>/reject", methods=["POST"])
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
        # Extract only the required fields for validation (exclude CSRF token)
        admin_data = {"admin_notes": request.form.get("admin_notes", "")}

        # Debug logging
        logger.info(f"Admin reject request data: {admin_data}")

        # Validate admin notes input
        is_valid, validated_data, errors = validate_request_data(
            AdminNotesSchema, admin_data
        )

        if not is_valid:
            logger.warning(f"Invalid admin notes in reject: {errors}")
            return jsonify({"error": "Invalid input data", "details": errors}), 400

        # Get sanitized admin notes
        admin_notes = SecurityValidation.sanitize_string(
            validated_data["admin_notes"], max_length=1000
        )
        admin_username = session.get("user", {}).get("username")

        # Validate admin username
        if not SecurityValidation.validate_username(admin_username):
            logger.error(f"Invalid admin username in reject: {admin_username}")
            return jsonify({"error": "Authentication error"}), 401

        # Get proposal details
        proposal = proposal_model.get_proposal_by_id(proposal_id)
        if not proposal:
            return jsonify({"error": "Proposal not found"}), 404

        if proposal["status"] != "pending":
            return jsonify({"error": f"Proposal is already {proposal['status']}"}), 400

        # Update proposal status to rejected
        success = proposal_model.update_proposal_status(
            proposal_id=proposal_id,
            status="rejected",
            admin_username=admin_username,
            admin_notes=admin_notes or "No reason provided",
        )

        if success:
            logger.info(f"Proposal {proposal_id} rejected by {admin_username}")
            return jsonify({"message": "Proposal rejected successfully."}), 200
        else:
            return jsonify({"error": "Failed to reject proposal"}), 500

    except Exception as e:
        logger.error(f"Error rejecting proposal {proposal_id}: {e}")
        return jsonify({"error": "Failed to reject proposal"}), 500
