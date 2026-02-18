"""
KE-WP Mapping Application
Refactored Flask application using modular blueprint architecture
"""
import logging
import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from src.utils.timezone import format_admin_timestamp
from src.utils.text import sanitize_log

# Import blueprints
from src.blueprints import admin_bp, api_bp, auth_bp, main_bp
from src.blueprints.admin import set_models as set_admin_models
from src.blueprints.api import set_models as set_api_models

# Import blueprint model setters
from src.blueprints.auth import set_models as set_auth_models
from src.blueprints.main import set_models as set_main_models

# Import configuration and services
from src.core.config import get_config
from src.core.error_handlers import register_error_handlers

# Import monitoring
from src.services.monitoring import monitor_performance
from src.services.rate_limiter import general_rate_limit
from src.services.container import ServiceContainer

# Load environment variables
load_dotenv(".env")  # Explicitly specify .env file

# Debug: Check if environment variables are loaded
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

required_vars = ["FLASK_SECRET_KEY", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]
for var in required_vars:
    value = os.getenv(var)
    logger.info(
        "%s: %s (%s)", var, 'SET' if value else 'NOT SET', '*' * min(len(value) if value else 0, 5) if value else 'None'
    )


def create_app(config_name: str = None):
    """
    Application factory function
    Creates and configures Flask application with blueprints

    Args:
        config_name: Configuration environment ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Ensure SECRET_KEY is set for Flask-WTF
    app.secret_key = config.FLASK_SECRET_KEY

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not config.DEBUG else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Initialize service container
    services = ServiceContainer(config)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Register error handlers
    register_error_handlers(app)

    # CSRF error handler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        logger.warning("CSRF error: %s from %s", sanitize_log(str(e.description)), sanitize_log(request.remote_addr))
        if request.is_json:
            return jsonify({"error": "CSRF token missing or invalid"}), 400
        return (
            render_template(
                "error.html", error="Security token expired. Please refresh the page."
            ),
            400,
        )

    # Initialize OAuth
    oauth = services.init_oauth(app)

    # Set up models for blueprints
    set_auth_models(services.github_client, guest_code=services.guest_code_model)
    set_api_models(
        services.mapping_model, services.proposal_model, services.cache_model,
        services.pathway_suggestion_service,
        go_suggestion_svc=services.go_suggestion_service,
        go_mapping=services.go_mapping_model,
        go_proposal=services.go_proposal_model,
        ke_meta=services.ke_metadata,
        pathway_meta=services.pathway_metadata,
    )
    set_admin_models(services.proposal_model, services.mapping_model, guest_code=services.guest_code_model)
    set_main_models(services.mapping_model, go_mapping=services.go_mapping_model)

    # Context processor to make is_admin available to all templates
    @app.context_processor
    def inject_user_context():
        """Inject user context including admin and guest status to all templates"""
        from flask import session

        user_data = session.get("user", {})
        current_user = user_data.get("username")
        is_guest = user_data.get("is_guest", False)

        if current_user:
            admin_users = os.getenv("ADMIN_USERS", "").split(",")
            admin_users = [user.strip() for user in admin_users if user.strip()]
            is_admin = current_user in admin_users
        else:
            is_admin = False

        return dict(is_admin=is_admin, is_guest=is_guest)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Health check and monitoring endpoints
    @app.route("/health")
    def health_check():
        """Simple health check endpoint"""
        try:
            health_status = services.get_health_status()
            return jsonify(
                {
                    "status": "healthy" if all(health_status.values()) else "degraded",
                    "timestamp": format_admin_timestamp(),
                    "version": "2.0.0",
                    "services": health_status,
                }
            )
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "timestamp": format_admin_timestamp(),
                        "error": "Health check failed",
                    }
                ),
                500,
            )

    @app.route("/metrics")
    @general_rate_limit
    def metrics():
        """Get system metrics (JSON API)"""
        return jsonify(services.metrics_collector.get_system_health())

    @app.route("/metrics/<endpoint_name>")
    @general_rate_limit
    def endpoint_metrics(endpoint_name):
        """Get metrics for a specific endpoint"""
        hours = request.args.get("hours", 24, type=int)
        return jsonify(services.metrics_collector.get_endpoint_stats(endpoint_name, hours))

    # Application teardown
    @app.teardown_appcontext
    def cleanup_services(error):
        """Cleanup services on app context teardown"""
        if error:
            logger.error("Application context error: %s", error)

    # Store service container for access by other modules
    app.service_container = services

    logger.info("Application initialized successfully with blueprint architecture")
    return app


# Create application instance for gunicorn/uwsgi
app = create_app()

if __name__ == "__main__":
    # Development server configuration
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")

    app.run(debug=debug_mode, host=host, port=port)
