#!/usr/bin/env python3
"""
Simple Socket.IO test server to isolate connection issues
"""

from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Create a minimal Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'

# Initialize CORS and Socket.IO with minimal configuration
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

@app.route('/')
def index():
    return "Socket.IO Test Server Running!"

@socketio.on('connect')
def test_connect():
    print(f"✅ Client connected: {request.sid}")
    emit('status', {'msg': 'Connected to test server'})
    return True

@socketio.on('disconnect')
def test_disconnect():
    print(f"❌ Client disconnected: {request.sid}")

@socketio.on('test_message')
def handle_test_message(data):
    print(f"📨 Received test message: {data}")
    emit('test_response', {'msg': 'Test message received', 'data': data})

if __name__ == '__main__':
    print("🚀 Starting Socket.IO Test Server...")
    print("🌐 Server will be available at: http://localhost:5002")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)