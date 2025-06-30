#FILE: services/voice_service.py
# ... imports ...

@socketio.on('stop_voice_stream')
def handle_stop_stream():
    from flask import session
    # This now correctly assumes the processing logic will be triggered
    # from here, likely by calling a function in ai_handler.py
    # from services.ai_handler import process_user_audio
    user_id = session.get('user_id')
    if user_id in user_audio_buffers:
        # ... logic ...
        # socketio.start_background_task(process_user_audio, user_id, audio_buffer)
