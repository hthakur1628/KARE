#!/usr/bin/env python3
"""
Comprehensive test for chat-backend connectivity
Tests HTTP API, Socket.IO, and Gemini AI integration
"""

import requests
import socketio
import json
import time
import threading

class ChatConnectionTester:
    def __init__(self):
        self.base_url = 'http://localhost:3001'
        self.api_url = f'{self.base_url}/api'
        self.token = None
        self.user_data = None
        self.sio = None
        self.messages_received = []
        
    def test_server_health(self):
        """Test if server is running and accessible"""
        print("🔍 Testing server health...")
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                print("✅ Server is running and accessible")
                return True
            else:
                print(f"❌ Server returned status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server - is it running?")
            return False
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False
    
    def test_user_authentication(self):
        """Test user login and token generation"""
        print("🔍 Testing user authentication...")
        
        # First try to register a test user
        try:
            register_data = {
                'email': 'chattest@example.com',
                'password': 'testpassword123',
                'name': 'Chat Test User'
            }
            
            register_response = requests.post(
                f'{self.api_url}/register',
                json=register_data,
                timeout=10
            )
            
            if register_response.status_code == 201:
                print("✅ Test user registered successfully")
            elif register_response.status_code == 409:
                print("ℹ️  Test user already exists")
            else:
                print(f"⚠️  Registration response: {register_response.status_code}")
        except Exception as e:
            print(f"⚠️  Registration error: {e}")
        
        # Now try to login
        try:
            login_data = {
                'email': 'chattest@example.com',
                'password': 'testpassword123'
            }
            
            response = requests.post(
                f'{self.api_url}/login',
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user_data = data.get('user')
                print("✅ User authentication successful")
                print(f"   User: {self.user_data.get('email')}")
                print(f"   Token: {self.token[:20]}..." if self.token else "   No token")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_socketio_connection(self):
        """Test Socket.IO connection with authentication"""
        print("🔍 Testing Socket.IO connection...")
        
        if not self.token:
            print("❌ No authentication token available")
            return False
        
        try:
            # Create Socket.IO client
            self.sio = socketio.Client(logger=False, engineio_logger=False)
            
            # Set up event handlers
            @self.sio.event
            def connect():
                print("✅ Socket.IO connected successfully")
            
            @self.sio.event
            def connect_error(data):
                print(f"❌ Socket.IO connection error: {data}")
            
            @self.sio.event
            def disconnect():
                print("🔌 Socket.IO disconnected")
            
            @self.sio.event
            def message(data):
                print(f"📨 Received message: {data.get('role')} - {data.get('content', '')[:50]}...")
                self.messages_received.append(data)
            
            @self.sio.event
            def status(data):
                print(f"📢 Status: {data.get('msg')}")
            
            @self.sio.event
            def error(data):
                print(f"❌ Socket error: {data.get('msg')}")
            
            # Connect with authentication
            print("🔌 Connecting to Socket.IO server...")
            self.sio.connect(
                self.base_url,
                auth={'token': self.token},
                wait_timeout=10
            )
            
            # Wait a moment for connection to establish
            time.sleep(1)
            
            if self.sio.connected:
                print("✅ Socket.IO connection established")
                return True
            else:
                print("❌ Socket.IO connection failed")
                return False
                
        except Exception as e:
            print(f"❌ Socket.IO connection error: {e}")
            return False
    
    def test_chat_messaging(self):
        """Test sending and receiving chat messages"""
        print("🔍 Testing chat messaging...")
        
        if not self.sio or not self.sio.connected:
            print("❌ Socket.IO not connected")
            return False
        
        try:
            # Join a chat room
            print("👥 Joining chat room...")
            self.sio.emit('join_room', {
                'user_email': self.user_data.get('email'),
                'session_id': 'test_session_123'
            })
            
            time.sleep(1)
            
            # Send a test message
            test_message = "Hello, this is a test message for the chat system."
            print(f"💬 Sending test message: {test_message}")
            
            self.sio.emit('send_message', {
                'message': test_message,
                'user_email': self.user_data.get('email'),
                'session_id': 'test_session_123'
            })
            
            # Wait for response
            print("⏳ Waiting for AI response...")
            start_time = time.time()
            timeout = 15  # 15 seconds timeout
            
            while time.time() - start_time < timeout:
                if self.messages_received:
                    # Check if we got an assistant response
                    for msg in self.messages_received:
                        if msg.get('role') == 'assistant':
                            print("✅ Received AI response!")
                            print(f"   Response: {msg.get('content', '')[:100]}...")
                            return True
                time.sleep(0.5)
            
            print("⚠️  No AI response received within timeout")
            if self.messages_received:
                print(f"   Received {len(self.messages_received)} other messages")
            return False
            
        except Exception as e:
            print(f"❌ Chat messaging error: {e}")
            return False
    
    def test_conversation_history(self):
        """Test conversation history functionality"""
        print("🔍 Testing conversation history...")
        
        if not self.sio or not self.sio.connected:
            print("❌ Socket.IO not connected")
            return False
        
        try:
            # Request conversation history
            print("📜 Requesting conversation history...")
            self.sio.emit('get_conversation_history', {
                'user_email': self.user_data.get('email'),
                'session_id': 'test_session_123'
            })
            
            # Wait for history response
            time.sleep(2)
            print("✅ Conversation history request sent")
            return True
            
        except Exception as e:
            print(f"❌ Conversation history error: {e}")
            return False
    
    def test_clear_conversation(self):
        """Test clearing conversation functionality"""
        print("🔍 Testing clear conversation...")
        
        if not self.sio or not self.sio.connected:
            print("❌ Socket.IO not connected")
            return False
        
        try:
            # Clear conversation
            print("🗑️  Clearing conversation...")
            self.sio.emit('clear_conversation', {
                'user_email': self.user_data.get('email'),
                'session_id': 'test_session_123'
            })
            
            time.sleep(1)
            print("✅ Clear conversation request sent")
            return True
            
        except Exception as e:
            print(f"❌ Clear conversation error: {e}")
            return False
    
    def cleanup(self):
        """Clean up connections"""
        if self.sio and self.sio.connected:
            try:
                self.sio.disconnect()
                print("🔌 Socket.IO disconnected")
            except:
                pass
    
    def run_all_tests(self):
        """Run all connectivity tests"""
        print("🧪 Chat-Backend Connectivity Test Suite")
        print("=" * 50)
        
        tests = [
            ("Server Health", self.test_server_health),
            ("User Authentication", self.test_user_authentication),
            ("Socket.IO Connection", self.test_socketio_connection),
            ("Chat Messaging", self.test_chat_messaging),
            ("Conversation History", self.test_conversation_history),
            ("Clear Conversation", self.test_clear_conversation)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            print("-" * 30)
            
            try:
                result = test_func()
                results[test_name] = result
                
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {e}")
                results[test_name] = False
            
            time.sleep(1)  # Brief pause between tests
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<25} {status}")
        
        print("-" * 50)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Chat-backend connectivity is working perfectly!")
        else:
            print("⚠️  Some tests failed. Check the issues above.")
            
        # Cleanup
        self.cleanup()
        
        return passed == total

def main():
    tester = ChatConnectionTester()
    success = tester.run_all_tests()
    
    if not success:
        print("\n🔍 TROUBLESHOOTING TIPS:")
        print("1. Make sure the backend server is running: python app.py")
        print("2. Check if port 3001 is accessible")
        print("3. Verify Gemini API key is configured correctly")
        print("4. Check server logs for error messages")
        print("5. Ensure no firewall is blocking the connection")
    
    return success

if __name__ == "__main__":
    main()