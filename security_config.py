import jwt
import datetime
import sqlite3
import logging
from flask import Flask, request, jsonify
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter

app = Flask(__name__)
SECRET_KEY = "your_strong_secret_key"

# 🔒 Enable Security Logging
logging.basicConfig(filename="assistant_security.log", level=logging.INFO)

# 🔒 OAuth Setup (Supports Microsoft, Anthropic, OpenAI, etc.)
oauth = OAuth(app)
oauth.register(
    name="microsoft",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    authorize_url="https://login.microsoftonline.com/YOUR_TENANT/oauth2/v2.0/authorize",
    access_token_url="https://login.microsoftonline.com/YOUR_TENANT/oauth2/v2.0/token"
)

# 🔒 Generate & Verify JWT Tokens
def generate_token(username, role):
    payload = {
        "username": username,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

# 🔒 Role-Based Access Control
def admin_only(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Missing token"}), 403
        user_data = verify_token(token.split("Bearer ")[-1])
        if not user_data or user_data.get("role") != "admin":
            return jsonify({"error": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return wrapper

# 🔒 Secure Database Query (Prevent SQL Injection)
def secure_query(username):
    conn = sqlite3.connect("secure_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    return cursor.fetchall()

# 🔒 API Rate Limiting (Prevent Abuse)
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route("/api/chat", methods=["POST"])
@limiter.limit("5 per minute")
def chat():
    return jsonify({"message": "Chat response from AI assistant"})

# 🔒 AI Assistant Configuration Endpoint
@app.route("/save_config", methods=["POST"])
def save_config():
    data = request.json
    logging.info(f"Configuration saved: {data}")
    return jsonify({"message": "Configuration saved successfully!"}), 200

# 🔒 Force HTTPS Only
@app.before_request
def force_https():
    if not request.is_secure:
        return jsonify({"error": "HTTPS required"}), 403

# 🔒 Provider Validation Before Accepting Configurations
@app.route("/validate_provider", methods=["POST"])
def validate_provider():
    data = request.json
    provider = data.get("aiProvider")

    required_fields = {
        "OpenAI": ["organizationNumber"],
        "Microsoft Copilot": [],
        "Google Gemini": [],
        "Anthropic": []
    }

    missing_fields = [field for field in required_fields.get(provider, []) if not data.get(field)]

    if missing_fields:
        logging.warning(f"Provider validation failed: Missing {missing_fields}")
        return jsonify({"approved": False, "message": f"Missing fields: {', '.join(missing_fields)}"}), 400

    return jsonify({"approved": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)