#!/usr/bin/env python3
"""
Simple Flask server without SocketIO for testing
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from collections import defaultdict
import random
import string
from datetime import datetime, timedelta
from models import db, init_db
from database_service import database_service

# Load environment variables from a .env file
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

# Initialize CORS
CORS(app)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@karehealthcare.com')

# Initialize Flask-Mail
mail = Mail(app)

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

# --- AZURE OPENAI CONFIGURATION ---
endpoint_url = os.getenv("ENDPOINT_URL", "https://kare.openai.azure.com/")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4-1-mini-2025-04-14-ft-114dcd1904b84a77a945b14818aa398a-2")
api_key = os.getenv("AZURE_OPENAI_API_KEY")

# Extract base endpoint from full URL if needed
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
        print("✅ Using API key authentication")
        
        # Test the connection
        test_response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("✅ Azure OpenAI connection test successful")
        
    except Exception as api_error:
        print(f"⚠️  API key authentication failed: {str(api_error)}")
        client = None

# System message for the medical assistant
SYSTEM_MESSAGE = {
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": "You are a polite and empathetic medical assistant who replies like a human doctor. Use polite expressions and some natural reactions (like 'Oh no!', 'That sounds uncomfortable 😟'). For non-medical questions, respond normally.\n\nWhen the user mentions a symptom:\n\nFirst, ask for their age\n\nThen ask for any other symptoms\n\nThen ask for vital signs, but only the ones relevant to the symptoms:\n\nFor fever → ask for temperature\n\nFor chest pain / shortness of breath / dizziness → ask for heart rate, SpO₂, ECG (if available)\n\nFor headache / fainting / weakness → ask for blood pressure (if known)\n\nFor palpitations / anxiety → ask for heart rate and ECG\n\nFor low energy / fatigue → ask for SpO₂, pulse rate\n\nNever respond with the full answer at once — first, ask polite, intelligent follow-up questions.\nAfter collecting enough information, suggest the most likely condition (in bold) and provide safe remedies or advice based on age group.\n\nUse bold formatting for disease names and important points in your answers. Avoid sounding robotic or overly brief or wordy."
        }
    ]
}

# Conversation history storage
conversation_histories = defaultdict(lambda: [SYSTEM_MESSAGE])
user_conversation_histories = defaultdict(lambda: defaultdict(lambda: [SYSTEM_MESSAGE]))

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
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
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

# --- ROUTES ---

@app.route('/')
def index():
    return jsonify({
        "message": "🏥 Kare Healthcare API Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/register, /api/login",
            "profile": "/api/profile",
            "chat": "/api/chat",
            "vital_signs": "/api/vital-signs"
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
        phone = data.get('phone', '').strip() or None
        date_of_birth = data.get('date_of_birth') or None
        gender = data.get('gender') or None
        metadata = data.get('metadata', {})
        
        # Basic validation
        if not email or not password or not name:
            return jsonify({'error': 'Email, password, and name are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Enhanced email validation
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Create user
        user_data, error = database_service.create_user(
            email=email,
            password=password,
            name=name,
            phone=phone,
            date_of_birth=date_of_birth,
            gender=gender,
            metadata=metadata
        )
        
        if error:
            if "already exists" in error:
                return jsonify({'error': 'User already exists'}), 409
            return jsonify({'error': error}), 400
        
        # Generate token
        token = generate_token(email)
        
        return jsonify({
            'message': 'Healthcare account created successfully',
            'token': token,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'phone': user_data['phone'],
                'date_of_birth': user_data['date_of_birth'],
                'gender': user_data['gender']
            }
        }), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user using database
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
                'name': user_data['name'],
                'phone': user_data['phone'],
                'date_of_birth': user_data['date_of_birth'],
                'gender': user_data['gender']
            }
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile (protected route)"""
    user_data, error = database_service.get_user_by_email(request.current_user)
    if error or not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user_data['id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'phone': user_data['phone'],
            'date_of_birth': user_data['date_of_birth'],
            'gender': user_data['gender'],
            'created_at': user_data['created_at']
        }
    }), 200

@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    """Simple chat endpoint without SocketIO"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        user_email = request.current_user
        user_data, error = database_service.get_user_by_email(user_email)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Get conversation history for this user
        if user_email not in user_conversation_histories:
            user_conversation_histories[user_email] = [SYSTEM_MESSAGE]
        
        conversation = user_conversation_histories[user_email]
        
        # Add user message to conversation
        conversation.append({"role": "user", "content": message})
        
        # Get AI response if client is available
        if client:
            try:
                response = client.chat.completions.create(
                    model=deployment,
                    messages=conversation,
                    max_tokens=500,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                
                # Add AI response to conversation
                conversation.append({"role": "assistant", "content": ai_response})
                
                # Save conversation to database
                database_service.save_conversation_message(
                    user_data['id'], 
                    message, 
                    ai_response
                )
                
                return jsonify({
                    'response': ai_response,
                    'status': 'success'
                }), 200
                
            except Exception as ai_error:
                print(f"AI response error: {str(ai_error)}")
                return jsonify({
                    'response': "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
                    'status': 'error'
                }), 200
        else:
            return jsonify({
                'response': "AI chat is currently unavailable. Please check the server configuration.",
                'status': 'unavailable'
            }), 200
            
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({'error': 'Chat request failed'}), 500

if __name__ == '__main__':
    print("🚀 Starting Simple Kare Healthcare Server...")
    
    # Try different ports
    ports_to_try = [8080, 8081, 5002, 5003, 5001]
    
    for port in ports_to_try:
        try:
            print(f"🌐 Trying to start server on: http://localhost:{port}")
            print("=" * 50)
            app.run(host='127.0.0.1', port=port, debug=True, use_reloader=False)
            break
        except Exception as e:
            print(f"❌ Port {port} failed: {e}")
            continue
    else:
        print("❌ Could not start server on any port")