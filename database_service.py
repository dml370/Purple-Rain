
# FILE: services/database_service.py
# Final, Unabridged Version: June 29, 2025

import logging
from cryptography.fernet import Fernet
import os
from models import db, User, AuthToken, UserProfile, Conversation
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# --- Field-Level Encryption Setup for API Keys ---
# This key MUST be set in your .env file and be a 32-byte URL-safe base64 key.
try:
    ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        raise ValueError("CRITICAL: FIELD_ENCRYPTION_KEY is not set for securing API keys.")
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    logger.exception("Failed to initialize encryption suite. API keys cannot be stored securely.")
    # This will cause the app to fail gracefully if the key is missing or invalid.
    raise

# --- User and Profile Functions ---

def get_user_by_id(user_id: str) -> User | None:
    """Fetches a user object from the database by their UUID."""
    return db.session.query(User).filter_by(id=user_id).first()

def get_or_create_user(email: str, name: str = None) -> User:
    """
    Retrieves a user by email. If they don't exist, a new user and their
    default profile are created. This is essential for the OAuth login flow.
    """
    user = db.session.query(User).filter_by(email=email).first()
    if user:
        return user
    
    try:
        new_user = User(email=email, name=name)
        new_profile = UserProfile(user=new_user)
        db.session.add(new_user)
        db.session.add(new_profile)
        db.session.commit()
        logger.info(f"New user and profile created for: {email}")
        return new_user
    except IntegrityError:
        db.session.rollback()
        logger.warning(f"Race condition during user creation for {email}. Fetching existing user.")
        return db.session.query(User).filter_by(email=email).first()

def save_user_profile(user_id: str, profile_data: dict):
    """Saves or updates a user's profile data."""
    profile = db.session.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        
    if 'ai_provider' in profile_data:
        profile.ai_provider = profile_data['ai_provider']
    if 'ai_model' in profile_data:
        profile.ai_model = profile_data['ai_model']
    if 'agent_personality' in profile_data:
        profile.agent_personality = profile_data['agent_personality']
    if 'core_principles' in profile_data:
        profile.core_principles = profile_data['core_principles']
    
    db.session.commit()
    logger.info(f"User profile updated for {user_id}.")

def get_user_profile(user_id: str) -> dict:
    """Retrieves a user's complete profile from the database."""
    profile = db.session.query(UserProfile).filter_by(user_id=user_id).first()
    if profile:
        return {
            "ai_provider": profile.ai_provider,
            "ai_model": profile.ai_model,
            "agent_personality": profile.agent_personality,
            "core_principles": profile.core_principles
        }
    return {}


# --- Authentication and Secure API Key Functions ---

def save_auth_token(user_id: str, provider_name: str, token: dict, api_key: str = None):
    """Saves or updates an OAuth token and/or securely encrypts and saves an API key."""
    auth_token = db.session.query(AuthToken).filter_by(user_id=user_id, provider_name=provider_name).first()
    if not auth_token:
        auth_token = AuthToken(user_id=user_id, provider_name=provider_name)
    
    auth_token.token = token
    if api_key:
        # Encrypt the key before saving to the database
        encrypted_key = cipher_suite.encrypt(api_key.encode())
        auth_token.api_key = encrypted_key
        
    db.session.add(auth_token)
    db.session.commit()
    logger.info(f"Auth token/API key for provider '{provider_name}' saved securely for user {user_id}.")

def get_user_api_key(user_id: str, provider_name: str) -> str | None:
    """Retrieves and decrypts a stored API key for a given user and AI provider."""
    token = db.session.query(AuthToken).filter_by(user_id=user_id, provider_name=provider_name).first()
    if token and token.api_key:
        try:
            decrypted_key = cipher_suite.decrypt(token.api_key)
            return decrypted_key.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key for user {user_id} and provider {provider_name}: {e}")
            return None
    return None


# --- Conversation History Functions ---

def add_to_conversation(user_id: str, message: dict):
    """Adds a new message to the conversation history."""
    # This is where the RAG service would be called to create an embedding for the message
    # from services.rag_service import rag_service
    # text_content = message.get('content')
    # if text_content and isinstance(text_content, str):
    #     rag_service.add_memory(user_id, text_content)

    convo_entry = Conversation(user_id=user_id, message=message)
    db.session.add(convo_entry)
    db.session.commit()

def get_conversation_history(user_id: str, limit: int = 50) -> list:
    """Retrieves the most recent conversation history for a user."""
    history = db.session.query(Conversation).filter_by(user_id=user_id).order_by(Conversation.timestamp.desc()).limit(limit).all()
    # Return in chronological order (oldest first) for the AI context
    return [h.message for h in reversed(history)]
