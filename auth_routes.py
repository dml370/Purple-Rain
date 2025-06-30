# FILE: routes/auth_routes.py

from flask import Blueprint, url_for, session, redirect, request, jsonify
from authlib.integrations.flask_client import OAuth
from services.database_service import get_or_create_user, save_auth_token, get_user_by_id
from config import Config
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def init_oauth(app):
    """Initializes the OAuth registry."""
    oauth.init_app(app)
    
    # --- Register Google for USER LOGIN ---
    # This is for authenticating users to our platform.
    oauth.register(
        name='google_login',
        client_id=Config.GOOGLE_LOGIN_CLIENT_ID,
        client_secret=Config.GOOGLE_LOGIN_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@auth_bp.route('/login')
def login():
    """Redirects user to Google to log in to our application."""
    # The URL to which Google will redirect the user back after authentication.
    redirect_uri = url_for('auth.authorize_login', _external=True)
    logger.info("Redirecting user to Google for login.")
    return oauth.google_login.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize_login')
def authorize_login():
    """Callback route for Google login. Handles the response from Google."""
    try:
        token = oauth.google_login.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            logger.error("Google OAuth failed: No userinfo in token.")
            return "Login failed: Could not retrieve user information.", 400
        
        # Create a new user in our database if they don't exist
        user = get_or_create_user(email=user_info['email'], name=user_info.get('name'))
        
        # Save their Google OAuth token
        save_auth_token(user_id=user.id, provider_name='google_login', token=token)
        
        # Create a secure session for the user
        session['user_id'] = user.id
        logger.info(f"User {user.email} successfully logged in and session created.")
        
        return redirect(url_for('main.main_interface'))
    except Exception as e:
        logger.error(f"Exception during Google OAuth callback: {e}")
        return "An error occurred during authentication.", 500

@auth_bp.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    user_id = session.pop('user_id', None)
    if user_id:
        logger.info(f"User {user_id} logged out.")
    return redirect(url_for('main.setup_page'))

# --- Routes for AI Provider Connections ---
# This is where the logic for the automated API key acquisition would live.
# As discussed, since many providers don't support a direct OAuth flow for this,
# the Bootstrap Agent will guide the user to their dashboard to get a key,
# which will then be saved via a secure API endpoint here.

@auth_bp.route('/api/save-api-key', methods=['POST'])
def save_api_key():
    """Secure endpoint for the user to submit an API key obtained from a provider."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    provider_name = data.get('provider')
    api_key = data.get('api_key')
    
    if not (provider_name and api_key):
        return jsonify({"error": "Provider and API key are required."}), 400
    
    # We save the key directly, as it's not from an OAuth token in this flow.
    # The 'token' column can be an empty JSON object.
    save_auth_token(
        user_id=session['user_id'], 
        provider_name=provider_name, 
        token={},
        api_key=api_key
    )
    
    return jsonify({"success": True, "message": f"{provider_name} API key has been securely saved."})
