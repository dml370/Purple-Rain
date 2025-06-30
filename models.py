# FILE: models.py
# Final, Unabridged Version: June 29, 2025

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

# This is the global database instance that will be initialized in app.py
db = SQLAlchemy()

class User(db.Model):
    """Represents a user of the application."""
    __tablename__ = 'users'
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships to other tables
    auth_tokens = relationship('AuthToken', back_populates='user', cascade="all, delete-orphan")
    profile = relationship('UserProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")
    conversations = relationship('Conversation', back_populates='user', cascade="all, delete-orphan")

class AuthToken(db.Model):
    """Stores encrypted API keys and OAuth tokens for various services."""
    __tablename__ = 'auth_tokens'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Stores the OAuth token data (access_token, refresh_token, etc.) as an encrypted JSON string.
    token: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # CORRECTED: Stores the securely encrypted API key as binary data, not plain text.
    api_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)

    user = relationship('User', back_populates='auth_tokens')

class UserProfile(db.Model):
    """Stores user-specific settings, including their chosen AI provider and personality."""
    __tablename__ = 'user_profiles'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)
    
    # Stores the chosen AI provider, e.g., 'openai'
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    # Stores the chosen model for that provider, e.g., 'gpt-4.5'
    ai_model: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Stores the user-defined personality for their agent
    agent_personality: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Stores the user's "Ten Commandments"
    core_principles: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    user = relationship('User', back_populates='profile')

class Conversation(db.Model):
    """Stores every turn of the conversation for long-term memory."""
    __tablename__ = 'conversations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    message: Mapped[dict] = mapped_column(JSON, nullable=False) # Stores role and content
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user = relationship('User', back_populates='conversations')
