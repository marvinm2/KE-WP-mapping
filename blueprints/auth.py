"""
Authentication Blueprint
Handles user login, logout, and OAuth flows
"""
import logging
import os

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, request, session, url_for

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


def init_oauth(app):
    """Initialize OAuth with the Flask app"""
    oauth = OAuth(app)
    github = oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
    return github


# Store github client globally (will be set by app initialization)
github_client = None


def set_models(client):
    """Set the GitHub OAuth client"""
    global github_client
    github_client = client


@auth_bp.route("/login")
def login():
    """Initiate GitHub OAuth login flow"""
    if not github_client:
        logger.error("GitHub OAuth client not initialized")
        return redirect(url_for("main.index"))

    redirect_uri = url_for("auth.authorize", _external=True)
    return github_client.authorize_redirect(redirect_uri)


@auth_bp.route("/callback")
def authorize():
    """Handle OAuth callback from GitHub"""
    try:
        if not github_client:
            logger.error("GitHub OAuth client not initialized")
            return redirect(url_for("main.index"))

        token = github_client.authorize_access_token()
        user_info = github_client.get("user").json()
        user_email = github_client.get("user/emails").json()

        # Validate user_info
        if not user_info or "login" not in user_info:
            logger.error("Failed to get user info from GitHub")
            return redirect(url_for("main.index"))

        # Store user info in session
        session["user"] = {
            "username": user_info["login"],
            "email": user_email[0]["email"]
            if user_email and len(user_email) > 0
            else "No public email",
        }
        logger.info(f"User {user_info['login']} logged in successfully")
        return redirect(url_for("main.index"))
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return redirect(url_for("main.index"))


@auth_bp.route("/logout")
def logout():
    """Log out the current user"""
    username = session.get("user", {}).get("username", "unknown")
    session.pop("user", None)
    logger.info(f"User {username} logged out")
    return redirect(url_for("main.index"))
