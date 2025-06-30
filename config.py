# FILE: config.py
# Final, Unabridged Version: June 29, 2025

import os
from dotenv import load_dotenv

# Load environment variables from a .env file at the project root.
load_dotenv()

class Config:
    """
    Central configuration for the AI Companion application.
    Loads all settings from environment variables for security and flexibility.
    This single class holds all necessary configuration for the platform.
    """

    # --- Core Flask & Application Settings ---

    # CRITICAL: A long, random string used for signing session cookies.
    # This MUST be set in your .env file.
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

    # The domain name of the server, required for generating external URLs
    # (e.g., in OAuth callbacks). Example: 'doitinglobal.info'
    SERVER_NAME = os.getenv('SERVER_NAME')

    # --- Database Configuration ---

    # The full connection string for the primary database.
    # The application will fail to start if this is not provided.
    # Example for Postgres: postgresql://user:password@host:port/dbname
    # Example for Oracle: oracle+oracledb://USER:PASSWORD@TNS_NAME
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    
    # Disables a feature of Flask-SQLAlchemy that is not needed and adds overhead.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Path to the Oracle Wallet, if using an Oracle Autonomous Database
    ORACLE_WALLET_PATH = os.getenv('ORACLE_WALLET_PATH')
    ORACLE_WALLET_PASSWORD = os.getenv('ORACLE_WALLET_PASSWORD')

    # --- Security, Licensing & Encryption ---

    # The master key for the primary (Bootstrap) server to GENERATE new license keys.
    # Must be a 32-byte URL-safe base64 key.
    LICENSE_MASTER_KEY = os.getenv('LICENSE_MASTER_KEY')
    
    # A separate key for encrypting/decrypting sensitive fields (like API keys) in the database.
    # Must also be a 32-byte URL-safe base64 key.
    FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')

    # For a deployed Personal Agent instance, this holds its own unique license key.
    LICENSE_KEY = os.getenv('LICENSE_KEY')

    # --- Google OAuth for User Login ---

    # Credentials from the Google Cloud Platform API & Services console for user authentication.
    GOOGLE_LOGIN_CLIENT_ID = os.getenv('GOOGLE_LOGIN_CLIENT_ID')
    GOOGLE_LOGIN_CLIENT_SECRET = os.getenv('GOOGLE_LOGIN_CLIENT_SECRET')

    # --- Bootstrap Agent Configuration ---

    # The provider and API key for the initial guidance agent that runs on your primary server.
    BOOTSTRAP_AGENT_PROVIDER = os.getenv('BOOTSTRAP_AGENT_PROVIDER', 'openai')
    BOOTSTRAP_AGENT_API_KEY = os.getenv('BOOTSTRAP_AGENT_API_KEY')
    
    # --- CORS (Cross-Origin Resource Sharing) Configuration ---

    # For production security, this should be the exact domain of your frontend application.
    CORS_ORIGIN = os.getenv('CORS_ORIGIN')

    # --- AI Provider Model Configuration ---

    # This dictionary defines the available models for the setup UI and can be
    # used by the Bootstrap agent to inform users of their choices.
    AI_PROVIDER_CONFIG = {
        'anthropic': {
            'models': {'text': ['claude-4-opus', 'claude-4-sonnet']},
            'required_fields': [],
        },
        'openai': {
            'models': {'text': ['gpt-4.5', 'o3-pro', 'o1-pro']},
            'required_fields': [],
        },
        'google': {
            'models': {'text': ['gemini-2.5-pro', 'gemini-2.5-flash']},
            'required_fields': [],
        },
        'microsoft': {
            'models': {'text': ['gpt-4.5', 'o3-pro']}, # Deployment names on Azure will vary
            'required_fields': ['endpoint', 'deploymentName'],
        },
        'oracle': {
            'models': {'text': ['grok-1', 'cohere.command-r-plus', 'meta.llama-3-70b-instruct']},
            'required_fields': ['compartmentOcid'],
        }
    }


# Create a single configuration object to be imported by the main app.
AppConfig = Config()
