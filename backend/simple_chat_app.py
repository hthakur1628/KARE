#!/usr/bin/env python3
"""
Simple Chat App with Gemini Integration - No Authentication
"""

import os
import google.generativeai as genai
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-chat-secret-key'

# Initialize CORS and Flask-SocketIO (simple configuration)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# --- GEMINI AI CONFIGURATION ---
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

print(f"🔧 Gemini AI Configuration:")
print(f"   Model: {gemini_model_name}")
print(f"   API Key: {'✅ Configured' if gemini_api_key else '❌ Not configured'}")

# Initialize Gemini client
gemini_model = None

if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel(gemini_model_name)
        
        # Test the connection
        test_response = gemini_model.generate_content("Hello, this is a test.")
        print("✅ Gemini AI connection test successful")
        print(f"   Test response: {test_response.text[:50]}...")
        
    except Exception as gemini_error:
        print(f"⚠️  Gemini AI authentication failed: {str(gemini_error)}")
        gemini_model = None
else:
    print("⚠️  No Gemini API key configured")
    gemini_model = None

# System prompt for Gemini
SYSTEM_PROMPT = """You are Kare, a polite and empathetic medical assistant who replies like a human doctor. Use polite expressions and some natural reactions (like 'Oh no!', 'That sounds uncomfortable 😟'). For non-medical questions, respond normally.

When the user mentions a symptom:

1. First, ask for their age
2. Then ask for any other symptoms
3. Then ask for vital signs, but only the ones relevant to the symptoms:
   - For fever → ask for temperature
   - For chest pain / shortness of breath / dizziness → ask for heart rate, SpO₂, ECG (if available)
   - For headache / fainting / weakness → ask for blood pressure (if known)
   - For palpitations / anxiety → ask for heart rate and ECG
   - For low energy / fatigue → ask for SpO₂, pulse rate

Never respond with the full answer at once — first, ask polite, intelligent follow-up questions.
After collecting enough information, suggest the most likely condition (in **bold**) and provide safe remedies or advice based on age group.

Use **bold formatting** for disease names and important points in your answers. Avoid sounding robotic or overly brief or wordy.

IMPORTANT: Always remind users that this is for informational purposes only and they should consult with a healthcare professional for proper diagnosis and treatment."""

# Conversation storage
user_conversations = defaultdict(list)

# --- SOCKET.IO HANDLERS ---

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"🔗 Client connected: {request.sid}")
    emit('status', {'msg': 'Connected to Kare Healthcare Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle user joining a chat room"""
    try:
        user_email = data.get('user_email', 'anonymous')
        join_room(user_email)
        print(f"👤 User {user_email} joined room")
        emit('status', {'msg': f'Joined chat room for {user_email}'})
    except Exception as e:
        print(f"❌ Error joining room: {str(e)}")
        emit('error', {'msg': 'Failed to join chat room'})

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming chat messages and generate AI responses"""
    try:
        user_message = data.get('message', '').strip()
        user_email = data.get('user_email', 'anonymous')
        session_id = data.get('session_id', request.sid)
        
        if not user_message:
            emit('error', {'msg': 'Message cannot be empty'})
            return
        
        print(f"💬 Received message from {user_email}: {user_message[:50]}...")
        
        # Store user message
        user_conversations[f"{user_email}_{session_id}"].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Echo user message
        emit('message', {
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'session_id': session_id
        }, room=user_email)
        
        # Generate AI response if Gemini is available
        if gemini_model:
            try:
                # Prepare conversation context
                conversation_key = f"{user_email}_{session_id}"
                conversation_history = user_conversations[conversation_key]
                
                # Build prompt with conversation history
                full_prompt = f"{SYSTEM_PROMPT}\n\nConversation History:\n"
                
                # Add last 10 messages for context
                for msg in conversation_history[-10:]:
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    full_prompt += f"{role}: {msg['content']}\n"
                
                full_prompt += f"\nUser: {user_message}\nAssistant:"
                
                # Generate response
                response = gemini_model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=1000,
                        top_p=0.8,
                        top_k=40
                    )
                )
                
                if response and response.text:
                    ai_response = response.text.strip()
                    
                    # Store AI response
                    user_conversations[conversation_key].append({
                        'role': 'assistant',
                        'content': ai_response,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Send AI response
                    emit('message', {
                        'role': 'assistant',
                        'content': ai_response,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'session_id': session_id
                    }, room=user_email)
                    
                    print(f"🤖 AI response sent to {user_email}")
                else:
                    emit('error', {'msg': 'Failed to generate AI response'})
                    
            except Exception as ai_error:
                print(f"❌ AI Error: {str(ai_error)}")
                emit('error', {'msg': 'AI service temporarily unavailable'})
        else:
            # Gemini not available
            fallback_message = "I'm sorry, but the AI assistant is currently unavailable. Please try again later."
            
            emit('message', {
                'role': 'assistant',
                'content': fallback_message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_id': session_id
            }, room=user_email)
            
    except Exception as e:
        print(f"❌ Message handling error: {str(e)}")
        emit('error', {'msg': 'Failed to process message'})

@socketio.on('clear_conversation')
def handle_clear_conversation(data):
    """Handle clearing conversation history"""
    try:
        user_email = data.get('user_email', 'anonymous')
        session_id = data.get('session_id', request.sid)
        
        # Clear conversation history
        conversation_key = f"{user_email}_{session_id}"
        if conversation_key in user_conversations:
            user_conversations[conversation_key].clear()
        
        emit('conversation_cleared', {'msg': 'Conversation history cleared'})
        print(f"🗑️  Conversation cleared for {user_email}")
        
    except Exception as e:
        print(f"❌ Clear conversation error: {str(e)}")
        emit('error', {'msg': 'Failed to clear conversation'})

@socketio.on('get_conversation_history')
def handle_get_conversation_history(data):
    """Handle getting conversation history"""
    try:
        user_email = data.get('user_email', 'anonymous')
        session_id = data.get('session_id', request.sid)
        
        # Get conversation history
        conversation_key = f"{user_email}_{session_id}"
        history = user_conversations.get(conversation_key, [])
        
        emit('conversation_history', {
            'history': history,
            'session_id': session_id
        })
        
        print(f"📜 Sent conversation history to {user_email}")
        
    except Exception as e:
        print(f"❌ Get conversation history error: {str(e)}")
        emit('error', {'msg': 'Failed to get conversation history'})

# --- BASIC ROUTES ---

@app.route('/')
def index():
    return "Kare Healthcare Chat Server is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "gemini": "available" if gemini_model else "unavailable"}

# --- MAIN APPLICATION STARTUP ---

if __name__ == '__main__':
    print("🚀 Starting Kare Healthcare Chat Server...")
    print("🌐 Server will be available at: http://localhost:5001")
    print("🔗 Frontend should connect to: http://localhost:5001")
    print("==================================================")
    
    # Run the application
    socketio.run(
        app,
        host='0.0.0.0',
        port=5001,
        debug=True,
        allow_unsafe_werkzeug=True
    )