
# FILE: app.py
# Final, Unabridged Version: June 29, 2025

import os
import sys
import logging
import logging.config
from flask import Flask
from flask_socketio import SocketIO
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_cors import CORS

# Import configurations and initializers
from config import AppConfig
from models import db
from routes.main_routes import main_bp
from routes.auth_routes import auth_bp, init_oauth
from services.license_service import validate_license_key
from oci_config import init_oracle_client

def validate_environment():
    """
    Checks for the presence of critical environment variables at startup.
    The application will fail to launch if any of these are missing.
    """
    required_vars = [
        'FLASK_SECRET_KEY', 'DATABASE_URI', 'LICENSE_MASTER_KEY', 
        'FIELD_ENCRYPTION_KEY', 'BOOTSTRAP_AGENT_API_KEY', 
        'GOOGLE_LOGIN_CLIENT_ID', 'GOOGLE_LOGIN_CLIENT_SECRET'
    ]
    
    # In production, CORS_ORIGIN is mandatory for security.
    if os.getenv('FLASK_ENV') == 'production':
        required_vars.append('CORS_ORIGIN')

    # For a deployed personal agent, its own license key is also required.
    if os.getenv('FLASK_ENV') == 'production' and not os.getenv('IS_BOOTSTRAP_SERVER'):
        required_vars.append('LICENSE_KEY')
        
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if missing_vars:
        logging.basicConfig(level=logging.CRITICAL)
        logging.critical(f"FATAL STARTUP ERROR: Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

# --- Run validation before doing anything else ---
validate_environment()

# --- Production-Grade Logging Configuration ---
LOGGING_CONFIG = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'json': {'()': 'pythonjsonlogger.jsonlogger.JsonFormatter', 'format': '%(asctime)s %(name)s %(levelname)s %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'json', 'stream': sys.stdout}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# --- License Validation for Deployed Personal Agent Instances ---
if os.getenv('FLASK_ENV') == 'production' and not os.getenv('IS_BOOTSTRAP_SERVER'):
    if not validate_license_key(os.getenv('LICENSE_KEY')):
        logger.critical("LICENSE VALIDATION FAILED. Application startup aborted.")
        sys.exit(1)
    logger.info("Instance license validated successfully.")

# --- Initialize Extensions Globally ---
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
migrate = Migrate()
cors = CORS()

def create_app(config_object=AppConfig):
    """
    Application factory pattern: creates and configures the Flask app.
    """
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    app.config.from_object(config_object)

    # Initialize extensions with the app instance
    db.init_app(app)
    
    # CORRECTED: Securely Initialize CORS from the environment variable
    CORS_ORIGIN = AppConfig.CORS_ORIGIN
    if CORS_ORIGIN:
        # Apply CORS to both standard Flask routes and SocketIO
        cors.init_app(app, resources={r"/api/*": {"origins": CORS_ORIGIN}})
        socketio.init_app(app, cors_allowed_origins=CORS_ORIGIN, async_mode='gevent')
        logger.info(f"CORS configured for specified origin: {CORS_ORIGIN}")
    else:
        # If no origin is specified (e.g., in local dev), use restrictive defaults.
        socketio.init_app(app, async_mode='gevent')
        logger.warning("CORS_ORIGIN not set. Cross-origin requests will be blocked by default.")
    
    limiter.init_app(app)
    migrate.init_app(app, db)
    init_oauth(app)
    Talisman(app) # Talisman for security headers

    # Register Blueprints to organize routes
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Initialize Oracle Client if configured for production
    if os.getenv('FLASK_ENV') == 'production' and "oracle" in AppConfig.SQLALCHEMY_DATABASE_URI:
        with app.app_context():
            init_oracle_client()
    
    logger.info("Flask application created and configured successfully.")
    return app

# --- Application Entry Point ---
app = create_app()

if __name__ == '__main__':
    # The port is driven by the PORT environment variable, defaulting to 8000.
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting AI Companion server on port {port}")
    # Use socketio.run() to correctly start the server with WebSocket support.
    socketio.run(app, host='0.0.0.0', port=port)
