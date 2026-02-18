"""
Authentication Blueprint
Handles user login, logout, and OAuth flows
"""
import logging
import os

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, render_template, request, session, url_for

from src.services.rate_limiter import submission_rate_limit

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
guest_code_model = None


def set_models(client, guest_code=None):
    """Set the GitHub OAuth client and guest code model"""
    global github_client, guest_code_model
    github_client = client
    guest_code_model = guest_code


@auth_bp.route("/login")
def login():
    """Initiate GitHub OAuth login flow"""
    if not github_client:
        logger.error("GitHub OAuth client not initialized")
        return redirect(url_for("main.index"))

    # Save return URL so we can redirect back after OAuth
    next_url = request.args.get("next") or request.referrer
    if next_url:
        session["login_next_url"] = next_url

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
        logger.info("User %s logged in successfully", user_info['login'])
        next_url = session.pop("login_next_url", None) or url_for("main.index")
        return redirect(next_url)
    except Exception as e:
        logger.error("OAuth callback error: %s", e)
        session.pop("login_next_url", None)
        return redirect(url_for("main.index"))


@auth_bp.route("/logout")
def logout():
    """Log out the current user"""
    username = session.get("user", {}).get("username", "unknown")
    session.pop("user", None)
    logger.info("User %s logged out", username)
    return redirect(url_for("main.index"))


@auth_bp.route("/guest-login")
def guest_login():
    """Render guest login form"""
    if session.get("user"):
        return redirect(url_for("main.index"))
    # Save return URL so we can redirect back after guest login
    next_url = request.args.get("next") or request.referrer
    if next_url:
        session["login_next_url"] = next_url
    return render_template("guest_login.html")


@auth_bp.route("/guest-login", methods=["POST"])
@submission_rate_limit
def guest_login_submit():
    """Validate guest access code and create session"""
    if session.get("user"):
        return redirect(url_for("main.index"))

    code = request.form.get("code", "").strip()
    if not code or not guest_code_model:
        return render_template("guest_login.html", error="Invalid access code.")

    result = guest_code_model.validate_code(code)
    if not result:
        logger.warning("Failed guest login attempt")
        return render_template("guest_login.html", error="Invalid, expired, or exhausted access code.")

    session["user"] = {
        "username": f"guest-{result['label']}",
        "email": "workshop-guest",
        "is_guest": True,
    }
    logger.info("Guest user logged in with label=%s", result["label"])
    next_url = session.pop("login_next_url", None) or url_for("main.index")
    return redirect(next_url)
