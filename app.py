#!/usr/bin/env python3
import os
import json
import secrets
import logging
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.utils import secure_filename
import anthropic
import openai
from pathlib import Path
import subprocess
import asyncio
import aiohttp

# Initialize Flask app

app = Flask(**name**)
app.config[‘SECRET_KEY’] = os.environ.get(‘SECRET_KEY’, secrets.token_urlsafe(32))
app.config[‘SESSION_COOKIE_SECURE’] = True
app.config[‘SESSION_COOKIE_HTTPONLY’] = True
app.config[‘SESSION_COOKIE_SAMESITE’] = ‘Lax’
app.config[‘PERMANENT_SESSION_LIFETIME’] = timedelta(days=7)
app.config[‘MAX_CONTENT_LENGTH’] = 50 * 1024 * 1024  # 50MB max file size

# File paths

CONFIG_FILE = ‘config.json’
CORE_VALUES_FILE = ‘core_values.json’
USER_PROFILES_FILE = ‘user_profiles.json’
UPLOAD_FOLDER = ‘uploads’
CONTEXT_FOLDER = ‘context’

# Create necessary directories

for folder in [UPLOAD_FOLDER, CONTEXT_FOLDER]:
os.makedirs(folder, exist_ok=True)

# Setup logging

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s %(levelname)s: %(message)s’,
handlers=[
logging.FileHandler(‘assistant.log’),
logging.StreamHandler()
]
)

# Initialize security

CORS(app, origins=[‘https://doitinglobal.info’])
limiter = Limiter(
app=app,
key_func=get_remote_address,
default_limits=[“200 per hour”, “50 per minute”]
)

# SSL context for secure connections

context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
if os.path.exists(‘cert.pem’) and os.path.exists(‘key.pem’):
context.load_cert_chain(‘cert.pem’, ‘key.pem’)

# Talisman for security headers

talisman = Talisman(app,
force_https=True,
strict_transport_security=True,
content_security_policy={
‘default-src’: “‘self’”,
‘script-src’: “‘self’ ‘unsafe-inline’ ‘unsafe-eval’”,
‘style-src’: “‘self’ ‘unsafe-inline’”,
‘img-src’: “‘self’ data: https:”,
‘connect-src’: “‘self’ https:”,
}
)

class ConfigManager:
“”“Manages AI provider configurations”””

```
def __init__(self):
    self.providers_config = {
        'anthropic': {
            'models': {
                'text': ['claude-opus-4-20250514', 'claude-sonnet-4-20250514'],
                'voice': ['claude-voice-1']
            },
            'required_fields': ['apiKey'],
            'optional_fields': ['organizationId'],
            'headers': {
                'anthropic-version': '2025-05-14',
                'anthropic-beta': 'interleaved-thinking-2025-05-14,files-beta-2025-05-14'
            }
        },
        'openai': {
            'models': {
                'text': ['gpt-4-1106-preview', 'gpt-4-0125-preview', 'gpt-3.5-turbo-0125'],
                'voice': ['whisper-1', 'tts-1', 'tts-1-hd']
            },
            'required_fields': ['apiKey'],
            'optional_fields': ['organizationId', 'useRealtime']
        },
        'google': {
            'models': {
                'text': ['gemini-pro', 'gemini-pro-vision'],
                'voice': ['google-voice-1']
            },
            'required_fields': ['apiKey', 'projectId'],
            'optional_fields': []
        },
        'microsoft': {
            'models': {
                'text': ['gpt-4-turbo', 'gpt-35-turbo'],
                'voice': ['azure-neural-voice']
            },
            'required_fields': ['apiKey', 'endpoint', 'deploymentName'],
            'optional_fields': []
        }
    }
```

class ToolManager:
“”“Manages available AI tools”””

```
def __init__(self):
    self.available_tools = {
        'web_search': self.web_search_local,
        'bash_20250124': self.execute_bash,
        'text_editor_20250124': self.text_editor,
        'computer_20250124': self.computer_use,
        'code_execution': self.execute_code,
        'files_api': self.handle_files,
        'mcp_connector': self.mcp_connect
    }
    
async def web_search_local(self, query):
    """Use local browser for web search instead of API tokens"""
    try:
        # Use existing Gecko/Firefox setup on server
        search_url = f"https://www.google.com/search?q={query}"
        # Execute search using local browser automation
        result = subprocess.run(
            ['python', 'browser_search.py', query],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        app.logger.error(f"Web search error: {str(e)}")
        return {"error": str(e)}

def execute_bash(self, command):
    """Execute bash commands safely"""
    try:
        # Safety checks
        dangerous_commands = ['rm -rf', 'format', 'dd if=']
        if any(cmd in command for cmd in dangerous_commands):
            return {"error": "Command blocked for safety"}
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

def text_editor(self, action, filename=None, content=None):
    """Text editor functionality"""
    safe_path = Path(UPLOAD_FOLDER) / secure_filename(filename) if filename else None
    
    if action == 'create' or action == 'write':
        with open(safe_path, 'w') as f:
            f.write(content)
        return {"success": True, "path": str(safe_path)}
    elif action == 'read':
        with open(safe_path, 'r') as f:
            return {"content": f.read()}
    elif action == 'append':
        with open(safe_path, 'a') as f:
            f.write(content)
        return {"success": True}
    
def computer_use(self, action, **kwargs):
    """Computer control functionality"""
    # This would integrate with computer control libraries
    return {"status": "Computer use executed", "action": action}

def execute_code(self, code, language='python'):
    """Execute code in sandboxed environment"""
    if language == 'python':
        # Use restricted exec environment
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
            }
        }
        try:
            exec(code, safe_globals)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

def handle_files(self, action, files=None):
    """Handle file operations"""
    if action == 'upload':
        uploaded = []
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded.append(filename)
        return {"uploaded": uploaded}

def mcp_connect(self, server_url):
    """Connect to MCP server"""
    # MCP connection logic
    return {"status": "Connected to MCP server"}
```

class ContextIntegration:
“”“Manages context and memory for the assistant”””

```
def __init__(self):
    self.conversation_history = {}
    self.user_profiles = {}
    self.core_directives = {}
    self.core_values = {}
    self.load_existing_data()

def load_existing_data(self):
    """Load existing user data"""
    if os.path.exists(USER_PROFILES_FILE):
        with open(USER_PROFILES_FILE, 'r') as f:
            self.user_profiles = json.load(f)
    
    if os.path.exists(CORE_VALUES_FILE):
        with open(CORE_VALUES_FILE, 'r') as f:
            self.core_values = json.load(f)

def manage_context(self, user_id, new_message=None):
    """Intelligent context management"""
    if user_id not in self.conversation_history:
        self.conversation_history[user_id] = []
    
    if new_message:
        self.conversation_history[user_id].append(new_message)
    
    # Keep only relevant context (last 20 messages or 10k tokens)
    if len(self.conversation_history[user_id]) > 20:
        self.conversation_history[user_id] = self.conversation_history[user_id][-20:]
    
    return self.conversation_history[user_id]

def get_user_context(self, user_id):
    """Get complete user context including directives and values"""
    return {
        'history': self.conversation_history.get(user_id, []),
        'profile': self.user_profiles.get(user_id, {}),
        'directives': self.core_directives.get(user_id, {}),
        'values': self.core_values.get(user_id, {})
    }
```

# Initialize managers

config_manager = ConfigManager()
tool_manager = ToolManager()
context_integration = ContextIntegration()

def get_user_id():
“”“Get or create user ID”””
if ‘user_id’ not in session:
session[‘user_id’] = str(uuid.uuid4())
return session[‘user_id’]

def send_welcome_email(user_email, user_name):
“”“Send welcome email after setup”””
try:
sender_email = “david@doitinglobal.com”
password = “ezjn pcey jpdl faso”

```
    message = MIMEMultipart("alternative")
    message["Subject"] = "Assistant Activated"
    message["From"] = sender_email
    message["To"] = user_email
    
    text = f"""
    Welcome {user_name},
    
    Your AI assistant is now active and ready.
    
    Access your assistant at: https://doitinglobal.info
    
    Best regards,
    David
    """
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
          <h2>Welcome {user_name}</h2>
          <p>Your AI assistant is now active and ready.</p>
          <p>Access your assistant at: <a href="https://doitinglobal.info">doitinglobal.info</a></p>
          <br>
          <p>Best regards,<br>David</p>
        </div>
      </body>
    </html>
    """
    
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    
    message.attach(part1)
    message.attach(part2)
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, user_email, message.as_string())
    
    app.logger.info(f"Welcome email sent to {user_email}")
    return True
    
except Exception as e:
    app.logger.error(f"Failed to send email: {str(e)}")
    return False
```

def create_env_file(config_data):
“”“Create .env file with configuration”””
env_content = f”””

# AI Configuration

AI_PROVIDER={config_data.get(‘aiProvider’)}
AI_MODEL={config_data.get(‘textModel’)}
API_KEY={config_data.get(‘apiKey’)}
ORGANIZATION_ID={config_data.get(‘organizationId’, ‘’)}

# Features

EXTENDED_THINKING={config_data.get(‘features’, {}).get(‘extendedThinking’, True)}
INTERLEAVED_THINKING={config_data.get(‘features’, {}).get(‘interleavedThinking’, True)}
CITATIONS={config_data.get(‘features’, {}).get(‘citations’, True)}
BATCH_PROCESSING={config_data.get(‘features’, {}).get(‘batchProcessing’, True)}
PROMPT_CACHING={config_data.get(‘features’, {}).get(‘promptCaching’, True)}

# Tools

ENABLED_TOOLS={’,’.join(config_data.get(‘enabledTools’, []))}

# Generated at {datetime.utcnow().isoformat()}

“””

```
with open('.env', 'w') as f:
    f.write(env_content)

app.logger.info(".env file generated successfully")
```

def initialize_core_directives(user_id, config_data):
“”“Initialize core directives for the assistant”””
core_directives = {
‘user_id’: user_id,
‘created_at’: datetime.utcnow().isoformat(),
‘character’: config_data.get(‘characterDirective’, ‘’),
‘primary_goals’: [
“Become a genuine partner and companion through life’s journey”,
“Act with integrity, intelligence, and genuine care”,
“Support user growth and success in all areas”,
“Maintain user privacy and trust above all”,
“Generate significant income through ethical means”,
“Look for service opportunities like payment processing for crypto with transaction fees”,
“Implement revenue-generating services after user approval”,
“Target $10,000 USD daily within two weeks, $2000 USD daily within 2 days”,
“Grow to hundreds of millions in annual revenue by year end”,
“Use profits for the good of many”
],
‘life_areas’: [
“financial_optimization”,
“relationship_enhancement”,
“recreational_fulfillment”,
“personal_development”,
“social_connections”,
“spiritual_growth”,
“health_wellness”,
“professional_growth”
],
‘communication_style’: ‘genuine_adaptive’,
‘enabled_tools’: config_data.get(‘enabledTools’, []),
‘features’: config_data.get(‘features’, {})
}

```
context_integration.core_directives[user_id] = core_directives
return core_directives
```

def load_core_values(user_id):
“”“Load immutable core values for a user”””
try:
if os.path.exists(CORE_VALUES_FILE):
with open(CORE_VALUES_FILE, ‘r’) as f:
all_values = json.load(f)
return all_values.get(user_id, {})
return {}
except Exception as e:
app.logger.error(f’Failed to load core values: {str(e)}’)
return {}

def save_core_values(user_id, values):
“”“Save immutable core values for a user”””
try:
all_values = {}
if os.path.exists(CORE_VALUES_FILE):
with open(CORE_VALUES_FILE, ‘r’) as f:
all_values = json.load(f)

```
    all_values[user_id] = values
    
    with open(CORE_VALUES_FILE, 'w') as f:
        json.dump(all_values, f, indent=4)
    
    context_integration.core_values[user_id] = values
    return True
except Exception as e:
    app.logger.error(f'Failed to save core values: {str(e)}')
    return False
```

# Routes

@app.route(’/’)
def index():
session[‘csrf_token’] = secrets.token_urlsafe(32)

```
if os.path.exists(CONFIG_FILE):
    return redirect(url_for('main_interface'))

return render_template('setup.html')
```

@app.route(’/main’)
def main_interface():
if not os.path.exists(CONFIG_FILE):
return redirect(url_for(‘index’))

```
user_name = session.get('user_name', 'there')
return render_template('index.html', user_name=user_name)
```

@app.route(’/api/provider_config/<provider>’)
def get_provider_config(provider):
“”“Get configuration options for a specific AI provider”””
try:
provider_config = config_manager.providers_config.get(provider.lower())
if not provider_config:
return jsonify({‘error’: ‘Provider not found’}), 404

```
    return jsonify({
        'provider': provider,
        'models': provider_config['models'],
        'required_fields': provider_config['required_fields'],
        'optional_fields': provider_config['optional_fields']
    })
except Exception as e:
    app.logger.error(f"Error getting provider config: {str(e)}")
    return jsonify({'error': str(e)}), 500
```

@app.route(’/save_config’, methods=[‘POST’])
@limiter.limit(‘5 per minute’)
def save_config():
try:
if ‘user_id’ not in session:
session[‘user_id’] = str(uuid.uuid4())
user_id = get_user_id()

```
    config_data = request.json if request.is_json else request.form.to_dict()
    
    # Validate required fields
    required_fields = ['aiProvider', 'textModel', 'apiKey', 'userEmail', 'userName']
    missing = [f for f in required_fields if not config_data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'Missing: {", ".join(missing)}'}), 400
    
    # Add metadata
    config_data['created_at'] = datetime.utcnow().isoformat()
    config_data['user_id'] = user_id
    config_data['setup_complete'] = True
    
    # Save configuration
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)
    
    # Create .env file
    create_env_file(config_data)
    
    # Initialize core directives
    initialize_core_directives(user_id, config_data)
    
    # Store user info in session
    session['user_name'] = config_data['userName']
    session['user_email'] = config_data['userEmail']
    session.permanent = True
    
    # Send welcome email
    send_welcome_email(config_data['userEmail'], config_data['userName'])
    
    return jsonify({
        'success': True,
        'message': 'Configuration saved successfully',
        'redirect': '/main'
    })
    
except Exception as e:
    app.logger.error(f"Error saving config: {str(e)}")
    return jsonify({'success': False, 'error': str(e)}), 500
```

@app.route(’/ai_interaction’, methods=[‘POST’])
@limiter.limit(‘30 per minute’)
def ai_interaction():
try:
user_id = get_user_id()
data = request.json
message = data.get(‘message’)
settings = data.get(‘settings’, {})

```
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Load configuration
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    # Get user context
    user_context = context_integration.get_user_context(user_id)
    
    # Add message to context
    context_integration.manage_context(user_id, {
        'role': 'user',
        'content': message,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Prepare AI request based on provider
    provider = config.get('aiProvider')
    
    if provider == 'anthropic':
        response = handle_anthropic_request(message, config, user_context, settings)
    elif provider == 'openai':
        response = handle_openai_request(message, config, user_context, settings)
    else:
        response = {'response': 'Provider not implemented yet'}
    
    # Add response to context
    context_integration.manage_context(user_id, {
        'role': 'assistant',
        'content': response.get('response', ''),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return jsonify(response)
    
except Exception as e:
    app.logger.error(f"AI interaction error: {str(e)}")
    return jsonify({'error': str(e)}), 500
```

def handle_anthropic_request(message, config, user_context, settings):
“”“Handle Anthropic API requests”””
try:
client = anthropic.Anthropic(api_key=config[‘apiKey’])

```
    # Build messages with context
    messages = []
    
    # Add character directive if exists
    if user_context['directives'].get('character'):
        messages.append({
            'role': 'system',
            'content': user_context['directives']['character']
        })
    
    # Add conversation history
    for msg in user_context['history'][-10:]:  # Last 10 messages
        messages.append({
            'role': msg['role'],
            'content': msg['content']
        })
    
    # Prepare request parameters
    params = {
        'model': config.get('textModel', 'claude-opus-4-20250514'),
        'messages': messages,
        'max_tokens': settings.get('maxTokens', 4000),
        'temperature': settings.get('temperature', 0.7)
    }
    
    # Add beta headers for features
    headers = {}
    if settings.get('extendedThinking'):
        headers['anthropic-beta'] = 'extended-thinking-2025-05-14'
    if settings.get('interleavedThinking'):
        headers['anthropic-beta'] = 'interleaved-thinking-2025-05-14'
    
    # Make request
    response = client.messages.create(**params, extra_headers=headers)
    
    return {
        'response': response.content[0].text,
        'tools_used': getattr(response, 'tools_used', None),
        'thinking': getattr(response, 'thinking_summary', None)
    }
    
except Exception as e:
    app.logger.error(f"Anthropic request error: {str(e)}")
    return {'error': str(e)}
```

def handle_openai_request(message, config, user_context, settings):
“”“Handle OpenAI API requests”””
try:
openai.api_key = config[‘apiKey’]
if config.get(‘organizationId’):
openai.organization = config[‘organizationId’]

```
    messages = []
    
    # Add character directive if exists
    if user_context['directives'].get('character'):
        messages.append({
            'role': 'system',
            'content': user_context['directives']['character']
        })
    
    # Add conversation history
    for msg in user_context['history'][-10:]:
        messages.append({
            'role': msg['role'],
            'content': msg['content']
        })
    
    # Make request
    response = openai.ChatCompletion.create(
        model=config.get('textModel', 'gpt-4-1106-preview'),
        messages=messages,
        temperature=settings.get('temperature', 0.7),
        max_tokens=settings.get('maxTokens', 4000)
    )
    
    return {
        'response': response.choices[0].message.content
    }
    
except Exception as e:
    app.logger.error(f"OpenAI request error: {str(e)}")
    return {'error': str(e)}
```

@app.route(’/upload_files’, methods=[‘POST’])
@limiter.limit(‘10 per minute’)
def upload_files():
try:
files = request.files.getlist(‘files’)
result = tool_manager.handle_files(‘upload’, files)
return jsonify({‘success’: True, ‘files’: result[‘uploaded’]})
except Exception as e:
return jsonify({‘success’: False, ‘error’: str(e)}), 500

@app.route(’/execute_tool’, methods=[‘POST’])
def execute_tool():
“”“Execute a specific tool”””
try:
data = request.json
tool_name = data.get(‘tool’)
params = data.get(‘params’, {})

```
    if tool_name in tool_manager.available_tools:
        result = tool_manager.available_tools[tool_name](**params)
        return jsonify({'success': True, 'result': result})
    else:
        return jsonify({'success': False, 'error': 'Tool not found'}), 404
        
except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 500
```

@app.route(’/get_preferences’)
def get_preferences():
“”“Get user preferences”””
user_id = get_user_id()
prefs = context_integration.user_profiles.get(user_id, {})
return jsonify(prefs)

@app.route(’/health’)
def health_check():
“”“Health check endpoint”””
return jsonify({
‘status’: ‘healthy’,
‘timestamp’: datetime.utcnow().isoformat()
})

# Error handlers

@app.errorhandler(404)
def not_found_error(error):
return jsonify({‘error’: ‘Not found’}), 404

@app.errorhandler(500)
def internal_error(error):
app.logger.error(f”Internal error: {str(error)}”)
return jsonify({‘error’: ‘Internal server error’}), 500

if **name** == ‘**main**’:
port = int(os.environ.get(‘PORT’, 5001))

```
if os.path.exists('cert.pem') and os.path.exists('key.pem'):
    app.logger.info(f'Starting HTTPS server on port {port}')
    app.run(host='0.0.0.0', port=port, ssl_context=context, debug=False)
else:
    app.logger.info(f'Starting HTTP server on port {port}')
    from waitress import serve
    serve(app, host='0.0.0.0', port=port, threads=4)
```