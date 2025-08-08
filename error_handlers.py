"""
Centralized Error Handling for KE-WP Mapping Application
Provides consistent error responses and logging across all blueprints
"""
import logging
from functools import wraps

from flask import jsonify, render_template, request
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    HTTPException,
    InternalServerError,
    NotFound,
    Unauthorized,
)

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base application error class"""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ApplicationError):
    """Validation error class"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 400, details)


class AuthenticationError(ApplicationError):
    """Authentication error class"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)


class AuthorizationError(ApplicationError):
    """Authorization error class"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403)


class NotFoundError(ApplicationError):
    """Not found error class"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ServiceError(ApplicationError):
    """External service error class"""

    def __init__(self, message: str = "External service error"):
        super().__init__(message, 503)


def register_error_handlers(app):
    """Register centralized error handlers with the Flask app"""

    @app.errorhandler(ApplicationError)
    def handle_application_error(error):
        """Handle custom application errors"""
        logger.error(f"Application error: {error.message} - Details: {error.details}")

        if (
            request.is_json
            or request.path.startswith("/api/")
            or request.path.startswith("/admin/")
        ):
            return (
                jsonify(
                    {
                        "error": error.message,
                        "details": error.details,
                        "status_code": error.status_code,
                    }
                ),
                error.status_code,
            )
        else:
            return (
                render_template(
                    "error.html", error=error.message, status_code=error.status_code
                ),
                error.status_code,
            )

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        logger.warning(f"Bad request: {request.url} - {error}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Invalid request data"}), 400
        else:
            return (
                render_template(
                    "error.html", error="Invalid request data", status_code=400
                ),
                400,
            )

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized errors"""
        logger.warning(f"Unauthorized access attempt: {request.url}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401
        else:
            return (
                render_template(
                    "error.html",
                    error="Please log in to access this page",
                    status_code=401,
                ),
                401,
            )

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors"""
        logger.warning(f"Forbidden access attempt: {request.url}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Access denied"}), 403
        else:
            return (
                render_template(
                    "error.html",
                    error="You do not have permission to access this resource",
                    status_code=403,
                ),
                403,
            )

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        logger.info(f"Page not found: {request.url}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        else:
            return (
                render_template(
                    "error.html",
                    error="The requested page was not found",
                    status_code=404,
                ),
                404,
            )

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle 429 Rate Limit errors"""
        logger.warning(f"Rate limit exceeded: {request.url} from {request.remote_addr}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Too many requests. Please try again later."}), 429
        else:
            return (
                render_template(
                    "error.html",
                    error="Too many requests. Please try again later.",
                    status_code=429,
                ),
                429,
            )

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {request.url} - {error}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        else:
            return (
                render_template(
                    "error.html",
                    error="An internal error occurred. Please try again later.",
                    status_code=500,
                ),
                500,
            )

    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle 503 Service Unavailable errors"""
        logger.error(f"Service unavailable: {request.url} - {error}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Service temporarily unavailable"}), 503
        else:
            return (
                render_template(
                    "error.html",
                    error="Service temporarily unavailable. Please try again later.",
                    status_code=503,
                ),
                503,
            )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.exception(f"Unexpected error: {request.url} - {str(error)}")

        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected error occurred"}), 500
        else:
            return (
                render_template(
                    "error.html",
                    error="An unexpected error occurred. Please try again later.",
                    status_code=500,
                ),
                500,
            )


def handle_errors(f):
    """Decorator to wrap route functions with error handling"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {f.__name__}: {e.message}")
            if request.is_json or request.path.startswith("/api/"):
                return (
                    jsonify({"error": e.message, "details": e.details}),
                    e.status_code,
                )
            else:
                return render_template("error.html", error=e.message), e.status_code
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {f.__name__}: {e.message}")
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": e.message}), e.status_code
            else:
                return render_template("error.html", error=e.message), e.status_code
        except Exception as e:
            logger.exception(f"Unexpected error in {f.__name__}: {str(e)}")
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "An unexpected error occurred"}), 500
            else:
                return (
                    render_template("error.html", error="An unexpected error occurred"),
                    500,
                )

    return decorated_function


def log_error_details(error: Exception, context: str = None):
    """Helper function to log error details with context"""
    context_str = f" in {context}" if context else ""
    logger.error(f"Error{context_str}: {str(error)}")
    logger.debug(f"Error details{context_str}:", exc_info=True)


def create_error_response(message: str, status_code: int = 500, details: dict = None):
    """Helper function to create consistent error responses"""
    if request.is_json or request.path.startswith("/api/"):
        response_data = {"error": message}
        if details:
            response_data["details"] = details
        return jsonify(response_data), status_code
    else:
        return (
            render_template("error.html", error=message, status_code=status_code),
            status_code,
        )
