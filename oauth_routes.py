from flask import Blueprint, redirect, request, session, jsonify
import os
import requests

oauth_blueprint = Blueprint('oauth', __name__)

@oauth_blueprint.route('/login/<provider>')
def oauth_login(provider):
    client_id = os.environ.get(f'{provider.upper()}_CLIENT_ID')
    redirect_uri = os.environ.get('OAUTH_REDIRECT_URI', 'https://yourdomain.com/oauth/callback')
    if not client_id:
        return jsonify({"error": "OAuth client ID not configured."}), 400

    # Construct the provider-specific authorization URL.
    auth_url = f"https://{provider}.com/oauth/authorize"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "profile email"
    }
    full_auth_url = requests.Request('GET', auth_url, params=params).prepare().url
    return redirect(full_auth_url)

@oauth_blueprint.route('/callback')
def oauth_callback():
    code = request.args.get('code')
    provider = request.args.get('provider')
    if not code or not provider:
        return jsonify({"error": "Missing code or provider parameter."}), 400

    token_url = f"https://{provider}.com/oauth/token"
    client_id = os.environ.get(f'{provider.upper()}_CLIENT_ID')
    client_secret = os.environ.get(f'{provider.upper()}_CLIENT_SECRET')
    redirect_uri = os.environ.get('OAUTH_REDIRECT_URI', 'https://yourdomain.com/oauth/callback')

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    token_response = requests.post(token_url, data=data)
    if token_response.status_code != 200:
        return jsonify({"error": "Token exchange failed."}), 400

    token_data = token_response.json()
    session['access_token'] = token_data.get('access_token')
    return jsonify({
        "message": "OAuth authentication successful.",
        "token": token_data.get('access_token')
    })