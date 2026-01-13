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

from timezone_utils import format_admin_timestamp

# Import blueprints
from blueprints import admin_bp, api_bp, auth_bp, main_bp
from blueprints.admin import set_models as set_admin_models
from blueprints.api import set_models as set_api_models

# Import blueprint model setters
from blueprints.auth import set_models as set_auth_models
from blueprints.main import set_models as set_main_models

# Import configuration and services
from config import get_config
from error_handlers import register_error_handlers

# Import monitoring
from monitoring import metrics_collector, monitor_performance
from rate_limiter import general_rate_limit
from services import ServiceContainer

# Load environment variables
load_dotenv(".env")  # Explicitly specify .env file

# Debug: Check if environment variables are loaded
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

required_vars = ["FLASK_SECRET_KEY", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]
for var in required_vars:
    value = os.getenv(var)
    logger.info(
        f"{var}: {'SET' if value else 'NOT SET'} ({'*' * min(len(value) if value else 0, 5) if value else 'None'})"
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
        logger.warning(f"CSRF error: {e.description} from {request.remote_addr}")
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
    set_auth_models(services.github_client)
    set_api_models(
        services.mapping_model, services.proposal_model, services.cache_model, services.pathway_suggestion_service
    )
    set_admin_models(services.proposal_model, services.mapping_model)
    set_main_models(services.mapping_model)

    # Context processor to make is_admin available to all templates
    @app.context_processor
    def inject_user_context():
        """Inject user context including admin status to all templates"""
        from flask import session

        current_user = session.get("user", {}).get("username")
        if current_user:
            admin_users = os.getenv("ADMIN_USERS", "").split(",")
            admin_users = [user.strip() for user in admin_users if user.strip()]
            is_admin = current_user in admin_users
        else:
            is_admin = False

        return dict(is_admin=is_admin)

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
            logger.error(f"Health check failed: {e}")
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "timestamp": format_admin_timestamp(),
                        "error": str(e),
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
            logger.error(f"Application context error: {error}")

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
