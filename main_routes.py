# FILE: routes/main_routes.py
# Final, Unabridged Version: June 29, 2025

import logging
from datetime import datetime
import psutil

from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from app import socketio, limiter
from services import ai_handler, database_service, license_service
from config import AppConfig

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


# --- HTML Serving Routes ---

@main_bp.route('/')
def setup_page():
    """
    Serves the initial page. If the user is already logged in (has a valid session),
    it redirects them directly to the main application interface. Otherwise, it shows
    the setup/login page.
    """
    if 'user_id' in session:
        return redirect(url_for('main.main_interface'))
    return render_template('setup.html')

@main_bp.route('/main')
def main_interface():
    """
    Primary application route for the main UI. This is the start_url for the PWA.
    It protects the route by redirecting any unauthenticated users to the setup/login page.
    """
    if 'user_id' not in session:
        return redirect(url_for('main.setup_page'))
    return render_template('index.html')


# --- API & Health Check Routes ---

@main_bp.route('/api/current_config')
def get_current_config():
    """Provides the current user's configuration to the main UI on page load."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    profile = database_service.get_user_profile(session['user_id'])
    provider = profile.get('ai_provider')
    
    # Default to the bootstrap provider if the user hasn't configured one yet
    if not provider:
        provider = AppConfig.BOOTSTRAP_AGENT_PROVIDER

    provider_config = AppConfig.AI_PROVIDER_CONFIG.get(provider, {})
    models = provider_config.get('models', {}).get('text', [])
    
    return jsonify({
        'provider': provider,
        'models': models,
        'selectedModel': profile.get('ai_model', models[0] if models else None)
    })

@main_bp.route('/api/user/settings', methods=['POST'])
@limiter.limit("30 per minute")
def update_user_settings():
    """Saves user's model selection or other profile settings to the database."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    database_service.save_user_profile(session['user_id'], data)
    
    return jsonify({"success": True, "message": "Settings updated."})

@main_bp.route('/health/detailed')
@limiter.exempt # Health checks should not be rate-limited
def health_check_detailed():
    """Detailed health check for container orchestration (e.g., Docker HEALTHCHECK)."""
    db_status = 'ok'
    try:
        # A simple, low-cost query to check if the database is responsive.
        database_service.db.session.execute('SELECT 1')
    except Exception as e:
        logger.error(f"Health check database connection failed: {e}")
        db_status = 'error'

    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_usage_percent": psutil.cpu_percent(),
        "memory_usage_percent": psutil.virtual_memory().percent,
        "database_status": db_status
    }), 200


# --- WebSocket Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handles new client connections and joins authenticated users to a private room."""
    if 'user_id' in session:
        user_id = session['user_id']
        join_room(user_id) # Private room for targeted emits
        logger.info(f"Authenticated user {user_id} connected and joined room {user_id}.")
        emit('status', {'msg': 'Connection to Personal Agent established.'})
    else:
        logger.info("An unauthenticated client connected for Bootstrap Agent interaction.")
        emit('status', {'msg': 'Connection to Bootstrap Agent established.'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('bootstrap_interaction')
async def handle_bootstrap_interaction(data):
    """Handles interactions with the initial Bootstrap Agent."""
    message_text = data.get('message', '')
    if not message_text:
        return
    
    # History for the bootstrap agent is ephemeral and not saved.
    messages = [{"role": "user", "content": message_text}]
    response = await ai_handler.get_bootstrap_response(messages)
    emit('bootstrap_response', response)

@socketio.on('personal_agent_interaction')
async def handle_personal_agent_interaction(data):
    """Handles interactions with the user's own Personal Agent."""
    if 'user_id' not in session:
        emit('error', {'message': 'Authentication required for Personal Agent.'})
        return

    user_id = session['user_id']
    message_text = data.get('message', '')
    image_data_url = data.get('image_data_url')

    # Construct the multimodal message payload
    message_content = []
    if message_text:
        message_content.append({"type": "text", "text": message_text})
    if image_data_url:
        image_b64 = image_data_url.split(',')[1]
        message_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": image_b64}
        })

    if not message_content:
        return

    latest_message_turn = {"role": "user", "content": message_content}
    
    # Save user's message to their long-term conversation history
    database_service.add_to_conversation(user_id, latest_message_turn)
    
    # The AI handler will use RAG to get relevant history. We pass only the latest message.
    response_data = await ai_handler.get_personal_agent_response(user_id, [latest_message_turn])
    
    if 'error' in response_data:
        emit('error', {'message': response_data['error']})
    else:
        emit('personal_agent_response', response_data)
        # Save AI's response to the long-term conversation history
        database_service.add_to_conversation(user_id, {"role": "assistant", "content": response_data.get('response')})
