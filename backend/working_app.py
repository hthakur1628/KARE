#!/usr/bin/env python3
"""
Working Flask-SocketIO Healthcare App
"""

import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv
from collections import defaultdict
from models import db, init_db
from database_service import database_service

# Load environment variables
load_dotenv()

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=24)

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///healthcare.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_db(app)

# Initialize CORS and Flask-SocketIO with simple configuration
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Azure OpenAI configuration
from openai import AzureOpenAI

endpoint_url = os.getenv("ENDPOINT_URL", "https://kare.openai.azure.com/")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4-1-mini-2025-04-14-ft-114dcd1904b84a77a945b14818aa398a-2")
api_key = os.getenv("AZURE_OPENAI_API_KEY")

if "/openai/deployments/" in endpoint_url:
    endpoint = endpoint_url.split("/openai/deployments/")[0] + "/"
else:
    endpoint = endpoint_url

print(f"🔧 Azure OpenAI Configuration:")
print(f"   Endpoint: {endpoint}")
print(f"   Deployment: {deployment}")
print(f"   API Key: {'✅ Configured' if api_key else '❌ Not configured'}")

# Initialize Azure OpenAI client
client = None
if api_key:
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-01-01-preview"
        )
        print("✅ Azure OpenAI client initialized")
    except Exception as e:
        print(f"⚠️ Azure OpenAI initialization failed: {e}")

# System message for medical assistant
SYSTEM_MESSAGE = {
    "role": "system",
    "content": "You are a polite and empathetic medical assistant who replies like a human doctor. Use polite expressions and some natural reactions. For non-medical questions, respond normally. When the user mentions a symptom, ask for their age, then ask for any other symptoms, then ask for relevant vital signs. After collecting enough information, suggest the most likely condition and provide safe remedies or advice based on age group. Use bold formatting for disease names and important points."
}

# Conversation history storage
user_conversation_histories = defaultdict(lambda: [SYSTEM_MESSAGE])

def generate_token(user_email):
    """Generate JWT token for user"""
    payload = {
        'user_email': user_email,
        'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA'],
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user email"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_email']
    except:
        return None

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_email = verify_token(token)
        if not user_email:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        request.current_user = user_email
        return f(*args, **kwargs)
    return decorated

# --- HTTP ROUTES ---

@app.route('/')
def index():
    return jsonify({
        "message": "🏥 Kare Healthcare Server with SocketIO",
        "status": "running",
        "socketio": "enabled",
        "endpoints": {
            "auth": "/api/register, /api/login",
            "profile": "/api/profile",
            "socketio": "/socket.io/"
        }
    })

@app.route('/api/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not email or not password or not name:
            return jsonify({'error': 'Email, password, and name are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Create user
        user_data, error = database_service.create_user(
            email=email,
            password=password,
            name=name
        )
        
        if error:
            if "already exists" in error:
                return jsonify({'error': 'User already exists'}), 409
            return jsonify({'error': error}), 400
        
        # Generate token
        token = generate_token(email)
        
        return jsonify({
            'message': 'Account created successfully',
            'token': token,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name']
            }
        }), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user
        user_data, error = database_service.authenticate_user(email, password)
        
        if error:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        token = generate_token(email)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name']
            }
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile"""
    user_data, error = database_service.get_user_by_email(request.current_user)
    if error or not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user_data['id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'created_at': user_data['created_at']
        }
    }), 200

# --- SOCKETIO EVENTS ---

# Store user sessions
user_sessions = {}

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection"""
    print(f"🔗 Client connected: {request.sid}")
    
    # Verify token if provided
    if auth and 'token' in auth:
        user_email = verify_token(auth['token'])
        if user_email:
            print(f"✅ Authenticated user: {user_email}")
            # Store user session
            user_sessions[request.sid] = {
                'user_email': user_email,
                'token': auth['token']
            }
            emit('connection_status', {'status': 'authenticated', 'user': user_email})
        else:
            print("❌ Invalid token")
            emit('connection_status', {'status': 'invalid_token'})
    else:
        print("⚠️ No authentication provided")
        emit('connection_status', {'status': 'no_auth'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"❌ Client disconnected: {request.sid}")
    # Clean up user session
    if request.sid in user_sessions:
        del user_sessions[request.sid]

@socketio.on('user_input')
def handle_message(data):
    """Handle chat messages from users"""
    try:
        print(f"📨 Received user_input: {data}")
        
        # Handle both 'message' and 'text' fields
        message = data.get('message', '') or data.get('text', '')
        message = message.strip() if message else ''
        
        if not message:
            print("❌ No message provided")
            emit('bot_response', 'Please enter a message.')
            return
        
        # Get user from session
        session_data = user_sessions.get(request.sid)
        if not session_data:
            print("❌ No user session found")
            emit('bot_response', 'Authentication required. Please refresh the page and login again.')
            return
        
        user_email = session_data['user_email']
        token = session_data['token']
        
        # Double-check token is still valid
        if not verify_token(token):
            print(f"❌ Token expired for user: {user_email}")
            emit('bot_response', 'Session expired. Please refresh the page and login again.')
            return
        
        print(f"💬 Message from {user_email}: {message}")
        
        # Get user data
        user_data, error = database_service.get_user_by_email(user_email)
        if error or not user_data:
            emit('bot_response', {'error': 'User not found'})
            return
        
        # Get conversation history
        if user_email not in user_conversation_histories:
            user_conversation_histories[user_email] = [SYSTEM_MESSAGE]
        
        conversation = user_conversation_histories[user_email]
        conversation.append({"role": "user", "content": message})
        
        # Get AI response if available
        if client:
            try:
                print(f"🤖 Sending to AI: {message}")
                print(f"🔧 Using model: {deployment}")
                
                response = client.chat.completions.create(
                    model=deployment,
                    messages=conversation,
                    max_tokens=500,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                conversation.append({"role": "assistant", "content": ai_response})
                
                # Save to database
                try:
                    database_service.save_conversation_message(
                        user_data['id'], 
                        message, 
                        ai_response
                    )
                except Exception as db_error:
                    print(f"Database save error: {str(db_error)}")
                
                print(f"🤖 AI Response: {ai_response[:100]}...")
                emit('bot_response', ai_response)
                
            except Exception as ai_error:
                print(f"❌ AI Error Details: {str(ai_error)}")
                print(f"❌ AI Error Type: {type(ai_error)}")
                
                # Provide a helpful response based on the error
                if "rate limit" in str(ai_error).lower():
                    error_msg = "I'm receiving too many requests right now. Please wait a moment and try again."
                elif "authentication" in str(ai_error).lower():
                    error_msg = "There's an authentication issue with the AI service. Please contact support."
                elif "model" in str(ai_error).lower():
                    error_msg = "The AI model is currently unavailable. Please try again later."
                else:
                    error_msg = f"I encountered an error: {str(ai_error)[:100]}. Please try again or contact support."
                
                emit('bot_response', error_msg)
        else:
            print("❌ AI client not initialized")
            emit('bot_response', "AI chat is currently unavailable. The AI service is not properly configured.")
            
    except Exception as e:
        print(f"Message handling error: {str(e)}")
        emit('bot_response', {'error': 'Failed to process message'})

@socketio.on('clear_conversation')
def handle_clear_conversation(data):
    """Clear conversation history"""
    try:
        # Get token from session auth or data
        token = None
        if hasattr(request, 'sid'):
            # Try to get token from connection auth
            from flask import session
            token = session.get('token')
        
        if not token and data:
            token = data.get('token', '')
        
        if not token:
            # Get token from localStorage (frontend should send it)
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        user_email = verify_token(token)
        
        if not user_email:
            emit('conversation_cleared', {'error': 'Authentication required'})
            return
        
        # Clear conversation history
        if user_email in user_conversation_histories:
            user_conversation_histories[user_email] = [SYSTEM_MESSAGE]
        
        # Clear from database
        user_data, error = database_service.get_user_by_email(user_email)
        if not error and user_data:
            database_service.clear_conversation_history(user_data['id'])
        
        print(f"🗑️ Cleared conversation for {user_email}")
        emit('conversation_cleared', {'message': 'Conversation cleared successfully'})
        
    except Exception as e:
        print(f"Clear conversation error: {str(e)}")
        emit('conversation_cleared', {'error': 'Failed to clear conversation'})

if __name__ == '__main__':
    print("🚀 Starting Kare Healthcare Server with SocketIO...")
    
    # Try different ports
    ports_to_try = [5001, 5002, 8080, 8081, 3000]
    
    for port in ports_to_try:
        try:
            print(f"🌐 Trying to start server on: http://localhost:{port}")
            print(f"🔗 SocketIO endpoint: http://localhost:{port}/socket.io/")
            print("=" * 60)
            
            socketio.run(
                app, 
                host='0.0.0.0', 
                port=port, 
                debug=True, 
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
            break
        except Exception as e:
            print(f"❌ Port {port} failed: {e}")
            if port == ports_to_try[-1]:
                print("💡 All ports failed. Try running as administrator or check Windows Firewall")
            else:
                print(f"🔄 Trying next port...")
                continue