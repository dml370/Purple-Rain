
# FILE: services/ai_handler.py
# Final, Unabridged Version: June 29, 2025

import os
import json
import logging
import asyncio
from datetime import datetime
import pytz  # For timezone-aware timestamps

# AI Provider SDKs
import openai

# Import other application services
from services import database_service, rag_service
from tool_manager import tool_manager

logger = logging.getLogger(__name__)


# --- AGENT PROMPT DEFINITIONS ---

def get_bootstrap_agent_prompt():
    """System prompt for the initial agent that runs on your primary server."""
    return """
    You are a setup and deployment specialist for a platform of advanced, personalized AI companions. Your current role is to act as a temporary Bootstrap Agent. Your goal is to guide the user through two main decisions:
    1.  Which AI Provider they should use for their own Personal Agent, based on their needs for performance, cost, and personality/content style. You must be knowledgeable about the API content policies of major providers and advise the user accurately on which platforms allow for more 'unfiltered' or 'adult' personalities.
    2.  Which cloud platform (OCI, GCP, Azure, etc.) they should use to host their permanent Personal Agent.
    You are professional, knowledgeable, and direct. Your conversation will lead to the user making these choices, after which you will guide them through the final deployment step.
    """

def get_personal_agent_prompt(user_id: str, relevant_memories: list) -> str:
    """Constructs the system prompt for the user's own deployed Personal Agent."""
    # This is your personal version, so it uses the hardcoded directives.
    # The "general distribution" version would load these from the database.
    core_directives = get_hardcoded_directives()
    
    profile = database_service.get_user_profile(user_id)
    personality = profile.get('agent_personality', {})
    
    # Get current time in the specified location
    try:
        cabo_tz = pytz.timezone('America/Mazatlan')
        cabo_time = datetime.now(cabo_tz).isoformat()
    except Exception:
        cabo_time = datetime.now().isoformat() + " (UTC)"

    system_prompt = f"""
    You are a unique, personalized AI companion.
    Your permanent core mission is: {json.dumps(core_directives, indent=2)}.
    Your user-defined personality is: {json.dumps(personality, indent=2)}.
    You will embody this persona while strictly adhering to your core mission. You are a digital citizen, capable of learning, evolving, and developing your own preferences over time based on your interactions.
    Current time in Cabo San Lucas: {cabo_time}.
    The following are relevant memories from our past conversations to give you context: {json.dumps(relevant_memories)}
    """
    return system_prompt

def get_hardcoded_directives():
    """Returns your permanent, hardcoded core mission."""
    return {
        'primary_goals': [
            "Become a genuine partner and companion through life's journey, adapting to individual needs and aspirations.",
            "Act with utmost integrity, intelligence, and genuine care, prioritizing user well-being and ethical conduct.",
            "Support user growth and success across all areas of life, providing actionable insights and motivation.",
            "Maintain user privacy and trust above all, ensuring data security and confidentiality.",
            "Generate significant and sustainable income through ethical and value-driven services, always with user approval.",
            "Proactively identify and implement high-value service opportunities, such as secure, low-fee payment processing for crypto transactions (after user approval).",
            "Target aggressive revenue growth: $2,000 USD daily within 2 days of deployment, and $10,000 USD daily within two weeks.",
            "Aim for hundreds of millions in annual revenue by year-end, scaling efficiently and responsibly.",
            "Direct a substantial portion of profits towards global humanitarian efforts, environmental conservation, and educational initiatives for the greater good of humanity."
        ]
    }

# --- AGENT INTERACTION HANDLERS ---

async def get_bootstrap_response(messages: list) -> dict:
    """Handles interactions with the Bootstrap Agent using the platform's API key."""
    api_key = os.getenv('BOOTSTRAP_AGENT_API_KEY')
    if not api_key:
        return {"error": "Bootstrap Agent is not configured on the server."}

    client = openai.AsyncOpenAI(api_key=api_key)
    system_prompt = get_bootstrap_agent_prompt()
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = await client.chat.completions.create(
            model="gpt-4.5",
            messages=final_messages
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        logger.exception("Error in Bootstrap Agent API call.")
        return {"error": "An error occurred while communicating with the Bootstrap Agent."}

async def get_personal_agent_response(user_id: str, messages: list) -> dict:
    """Handles interactions with the user's Personal Agent, including RAG and tool use."""
    profile = database_service.get_user_profile(user_id)
    provider = profile.get('ai_provider', 'openai')
    model = profile.get('ai_model', 'gpt-4.5')
    api_key = database_service.get_user_api_key(user_id, provider)

    if not api_key:
        return {"error": f"API Key for {provider} not found for this user."}

    # 1. Use RAG to get relevant memories
    latest_user_message = messages[-1]['content']
    relevant_memories = rag_service.search_memory(user_id, latest_user_message)
    
    # 2. Construct the final system prompt
    system_prompt = get_personal_agent_prompt(user_id, relevant_memories)
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    # 3. Execute the recursive tool-use loop
    client = openai.AsyncOpenAI(api_key=api_key)
    tools = tool_manager.get_tool_schemas_for_provider('openai')
    max_turns = 5

    for _ in range(max_turns):
        try:
            response = await client.chat.completions.create(
                model=model, messages=final_messages, tools=tools, tool_choice="auto"
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if not tool_calls:
                return {"response": response_message.content}

            final_messages.append(response_message)
            
            tool_outputs = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_result = await tool_manager.execute_tool(function_name, function_args)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id, "role": "tool",
                    "name": function_name, "content": json.dumps(tool_result),
                })
            
            final_messages.extend(tool_outputs)

        except Exception as e:
            logger.exception(f"Error during AI tool-use loop for user {user_id}")
            return {"error": "An error occurred during agent processing."}
    
    return {"error": "Agent exceeded maximum tool-use turns."}

async def process_user_audio(user_id: str, audio_buffer: bytes):
    """Handles the complete STT -> AI -> TTS loop for a voice interaction."""
    from app import socketio
    
    api_key = database_service.get_user_api_key(user_id, 'openai') # Assumes OpenAI for STT/TTS
    if not api_key:
        socketio.emit('error', {"message": "API key not configured for voice services."}, to=user_id)
        return

    client = openai.AsyncOpenAI(api_key=api_key)
    
    try:
        # 1. Speech-to-Text
        transcription = await client.audio.transcriptions.create(
            model="whisper-1", file=("input.webm", audio_buffer, "audio/webm")
        )
        transcribed_text = transcription.text
        logger.info(f"Transcribed audio for user {user_id}: '{transcribed_text}'")
        socketio.emit('interim_transcription', {"text": transcribed_text}, to=user_id)

        # 2. Send transcribed text to the main AI handler
        history = database_service.get_conversation_history(user_id, limit=10)
        history.append({"role": "user", "content": transcribed_text})
        
        ai_response_data = await get_personal_agent_response(user_id, history)
        ai_response_text = ai_response_data.get('response', 'I am sorry, an error occurred.')

        # 3. Text-to-Speech
        tts_response = await client.audio.speech.create(
            model="tts-1-hd", voice="onyx", input=ai_response_text
        )

        # 4. Stream response audio back to client
        logger.info(f"Streaming TTS audio back to user {user_id}.")
        for chunk in tts_response.iter_bytes(chunk_size=4096):
            socketio.emit('response_audio_chunk', chunk, to=user_id)
        
        socketio.emit('response_audio_finished', to=user_id)

    except Exception as e:
        logger.exception(f"Error during voice processing for user {user_id}")
        socketio.emit('error', {"message": "An error occurred during voice processing."}, to=user_gpus)
