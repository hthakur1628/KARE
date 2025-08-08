import os
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
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

# Initialize CORS and Flask-SocketIO
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

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

# --- 2. AZURE OPENAI CONFIGURATION ---

# Get Azure OpenAI configuration from environment variables
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

# Try API key authentication first (more reliable for development)
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
        
        # Try Entra ID authentication as fallback
        try:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2025-01-01-preview"
            )
            print("✅ Using Entra ID authentication as fallback")
            
        except Exception as entra_error:
            print(f"⚠️  Entra ID authentication also failed: {str(entra_error)}")
            print("⚠️  The application will run without AI chat functionality")
            client = None
else:
    print("⚠️  No API key configured")
    print("⚠️  The application will run without AI chat functionality")
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

# --- 3. USER STORAGE AND AUTHENTICATION ---
# Using SQLite database for user storage
user_sessions = {}  # Format: {session_id: session_data}

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

# --- 4. CONVERSATION HISTORY STORAGE ---
# Dictionary to store conversation history per user session (OpenAI format)
conversation_histories = defaultdict(lambda: [SYSTEM_MESSAGE])
user_conversation_histories = defaultdict(lambda: defaultdict(lambda: [SYSTEM_MESSAGE]))

# Clear all existing conversations to ensure new system message is used
conversation_histories.clear()

# --- 5. HTTP ROUTES ---

@app.route('/')
def index():
    return "Flask and Socket.IO server is running!"

@app.route('/socketio_test.html')
def socketio_test():
    """Serve the Socket.IO test page"""
    from flask import send_from_directory
    import os
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_from_directory(frontend_path, 'socketio_test.html')

@app.route('/api/register', methods=['POST'])
def register():
    """User registration endpoint with comprehensive health profile"""
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
        
        # Age validation if date_of_birth is provided
        if date_of_birth:
            try:
                from datetime import datetime, date
                birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                
                if age < 13:
                    return jsonify({'error': 'You must be at least 13 years old to create an account'}), 400
                if age > 120:
                    return jsonify({'error': 'Please enter a valid date of birth'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid date of birth format'}), 400
        
        # Create user with comprehensive data
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
        
        # Return comprehensive user data (excluding sensitive health info in response)
        return jsonify({
            'message': 'Healthcare account created successfully',
            'token': token,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'phone': user_data['phone'],
                'date_of_birth': user_data['date_of_birth'],
                'gender': user_data['gender'],
                'has_health_profile': bool(
                    user_data.get('height') or 
                    user_data.get('weight') or 
                    user_data.get('blood_type') or 
                    user_data.get('allergies') or 
                    user_data.get('current_medications') or 
                    user_data.get('medical_conditions')
                ),
                'has_emergency_contact': bool(user_data.get('emergency_contact_name')),
                'marketing_emails_consent': user_data.get('marketing_emails_consent', False),
                'sms_notifications_consent': user_data.get('sms_notifications_consent', False)
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

# --- FORGOT PASSWORD ENDPOINTS ---

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp, user_name):
    """Send OTP via email"""
    try:
        msg = Message(
            subject='Kare Healthcare - Password Reset OTP',
            recipients=[email],
            html=f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #2563eb, #06b6d4); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">Kare Healthcare</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Your Trusted Healthcare Assistant</p>
                </div>
                
                <div style="background: #f8fafc; padding: 30px; border-radius: 10px; margin-bottom: 30px;">
                    <h2 style="color: #1e40af; margin-bottom: 20px;">Password Reset Request</h2>
                    <p style="color: #374151; font-size: 16px; line-height: 1.6;">
                        Hello {user_name},<br><br>
                        We received a request to reset your password for your Kare Healthcare account. 
                        Use the OTP below to proceed with resetting your password:
                    </p>
                    
                    <div style="background: white; border: 2px solid #2563eb; border-radius: 10px; padding: 20px; text-align: center; margin: 30px 0;">
                        <p style="color: #6b7280; margin: 0 0 10px 0; font-size: 14px;">Your OTP Code:</p>
                        <h1 style="color: #2563eb; font-size: 36px; font-weight: bold; margin: 0; letter-spacing: 8px;">{otp}</h1>
                        <p style="color: #ef4444; margin: 15px 0 0 0; font-size: 14px;">⏰ This OTP will expire in 10 minutes</p>
                    </div>
                    
                    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                        <p style="color: #92400e; margin: 0; font-size: 14px;">
                            <strong>Security Note:</strong> If you didn't request this password reset, please ignore this email. 
                            Your account remains secure.
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; color: #6b7280; font-size: 14px;">
                    <p>This is an automated message from Kare Healthcare. Please do not reply to this email.</p>
                    <p>&copy; 2024 Kare Healthcare. All rights reserved.</p>
                </div>
            </div>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        return False

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Send OTP for password reset"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if user exists
        user_data, error = database_service.get_user_by_email(email)
        
        if error or not user_data:
            return jsonify({'error': 'Email not registered. Please check your email address or create a new account.'}), 404
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP with expiration (10 minutes)
        otp_storage[email] = {
            'otp': otp,
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'user_id': user_data['id'],
            'attempts': 0
        }
        
        # Send OTP via email
        if send_otp_email(email, otp, user_data['name']):
            return jsonify({
                'message': 'OTP sent successfully to your email address',
                'email': email
            }), 200
        else:
            return jsonify({'error': 'Failed to send OTP. Please try again later.'}), 500
            
    except Exception as e:
        print(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP for password reset"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        otp = data.get('otp', '').strip()
        
        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400
        
        # Check if OTP exists
        if email not in otp_storage:
            return jsonify({'error': 'No OTP found. Please request a new one.'}), 400
        
        otp_data = otp_storage[email]
        
        # Check if OTP is expired
        if datetime.utcnow() > otp_data['expires_at']:
            del otp_storage[email]
            return jsonify({'error': 'OTP has expired. Please request a new one.'}), 400
        
        # Check attempts limit
        if otp_data['attempts'] >= 3:
            del otp_storage[email]
            return jsonify({'error': 'Too many failed attempts. Please request a new OTP.'}), 400
        
        # Verify OTP
        if otp != otp_data['otp']:
            otp_storage[email]['attempts'] += 1
            remaining_attempts = 3 - otp_storage[email]['attempts']
            return jsonify({
                'error': f'Invalid OTP. {remaining_attempts} attempts remaining.'
            }), 400
        
        # OTP is valid - generate reset token
        reset_token = generate_token(email)
        
        # Update OTP data to mark as verified
        otp_storage[email]['verified'] = True
        otp_storage[email]['reset_token'] = reset_token
        
        return jsonify({
            'message': 'OTP verified successfully',
            'reset_token': reset_token
        }), 200
        
    except Exception as e:
        print(f"OTP verification error: {str(e)}")
        return jsonify({'error': 'Failed to verify OTP'}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password after OTP verification"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        reset_token = data.get('reset_token', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not email or not reset_token or not new_password:
            return jsonify({'error': 'Email, reset token, and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Verify reset token
        user_email = verify_token(reset_token)
        if not user_email or user_email != email:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Check if OTP was verified
        if email not in otp_storage or not otp_storage[email].get('verified'):
            return jsonify({'error': 'OTP not verified. Please verify OTP first.'}), 400
        
        # Get user data
        user_data, error = database_service.get_user_by_email(email)
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password
        success, update_error = database_service.update_user_password(user_data['id'], new_password)
        
        if update_error:
            return jsonify({'error': update_error}), 400
        
        # Clean up OTP storage
        if email in otp_storage:
            del otp_storage[email]
        
        return jsonify({
            'message': 'Password reset successfully. You can now login with your new password.'
        }), 200
        
    except Exception as e:
        print(f"Password reset error: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500


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

@app.route('/api/clear-cache')
@token_required
def clear_cache():
    """Clear conversation histories for current user"""
    user_email = request.current_user
    user_data, error = database_service.get_user_by_email(user_email)
    
    if error or not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    # Clear from database
    deleted_count, db_error = database_service.clear_conversation_history(user_data['id'])
    
    # Also clear from memory
    if user_email in user_conversation_histories:
        user_conversation_histories[user_email].clear()
    
    return {"status": "success", "message": f"Cleared {deleted_count or 0} conversation messages"}

@app.route('/api/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update user profile (protected route)"""
    try:
        data = request.get_json()
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user data with comprehensive profile information
        updated_user, update_error = database_service.update_user_profile(
            user_data['id'],
            name=data.get('name'),
            phone=data.get('phone'),
            date_of_birth=data.get('date_of_birth'),
            gender=data.get('gender'),
            metadata=data.get('metadata', {})
        )
        
        if update_error:
            return jsonify({'error': update_error}), 400
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': updated_user
        }), 200
        
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Profile update failed'}), 500

@app.route('/api/profile/stats', methods=['GET'])
@token_required
def get_profile_stats():
    """Get user profile statistics (protected route)"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user statistics
        user_id = user_data['id']
        
        # Count vital signs records
        vital_signs_count, _ = database_service.get_vital_signs_count(user_id)
        
        # Count conversations
        conversation_count, _ = database_service.get_conversation_count(user_id)
        
        # Count medical history entries
        medical_history_count, _ = database_service.get_medical_history_count(user_id)
        
        # Get recent activity (last 5 activities)
        recent_activities = []
        
        # Get latest vital signs entry
        latest_vitals, _ = database_service.get_latest_vital_signs(user_id)
        if latest_vitals:
            recent_activities.append({
                'type': 'vital_signs',
                'title': 'Vital signs recorded',
                'time': latest_vitals.get('recorded_at'),
                'icon': 'chart'
            })
        
        # Get recent conversations
        recent_conversations, _ = database_service.get_recent_conversations(user_id, limit=2)
        if recent_conversations:
            for conv in recent_conversations:
                recent_activities.append({
                    'type': 'conversation',
                    'title': 'Chat session',
                    'time': conv.get('created_at'),
                    'icon': 'chat'
                })
        
        # Sort activities by time (most recent first)
        recent_activities.sort(key=lambda x: x.get('time', ''), reverse=True)
        recent_activities = recent_activities[:5]  # Limit to 5 most recent
        
        return jsonify({
            'stats': {
                'total_checkups': conversation_count or 0,
                'vital_records': vital_signs_count or 0,
                'medical_conditions': medical_history_count or 0,
                'recent_activities': recent_activities
            }
        }), 200
        
    except Exception as e:
        print(f"Profile stats error: {str(e)}")
        return jsonify({'error': 'Failed to get profile statistics'}), 500

@app.route('/api/vital-signs', methods=['POST'])
@token_required
def save_vital_signs():
    """Save vital signs for current user"""
    try:
        data = request.get_json()
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Save vital signs
        vital_id, vital_error = database_service.save_vital_signs(
            user_data['id'],
            temperature=data.get('temperature'),
            heart_rate=data.get('heart_rate'),
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            oxygen_saturation=data.get('oxygen_saturation'),
            weight=data.get('weight'),
            height=data.get('height'),
            notes=data.get('notes')
        )
        
        if vital_error:
            return jsonify({'error': vital_error}), 400
        
        return jsonify({
            'message': 'Vital signs saved successfully',
            'vital_id': vital_id
        }), 201
        
    except Exception as e:
        print(f"Vital signs save error: {str(e)}")
        return jsonify({'error': 'Failed to save vital signs'}), 500

@app.route('/api/vital-signs', methods=['GET'])
@token_required
def get_vital_signs():
    """Get vital signs history for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        limit = request.args.get('limit', 10, type=int)
        vital_signs, vital_error = database_service.get_vital_signs_history(user_data['id'], limit)
        
        if vital_error:
            return jsonify({'error': vital_error}), 400
        
        return jsonify({
            'vital_signs': vital_signs
        }), 200
        
    except Exception as e:
        print(f"Vital signs get error: {str(e)}")
        return jsonify({'error': 'Failed to get vital signs'}), 500

@app.route('/api/vital-signs/latest', methods=['GET'])
@token_required
def get_latest_vital_signs():
    """Get latest vital signs for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        vital_signs, vital_error = database_service.get_latest_vital_signs(user_data['id'])
        
        if vital_error:
            return jsonify({'error': vital_error}), 404
        
        return jsonify({
            'vital_signs': vital_signs
        }), 200
        
    except Exception as e:
        print(f"Latest vital signs get error: {str(e)}")
        return jsonify({'error': 'Failed to get latest vital signs'}), 500

@app.route('/api/medical-history', methods=['POST'])
@token_required
def add_medical_condition():
    """Add medical condition to user's history"""
    try:
        data = request.get_json()
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        condition_name = data.get('condition_name')
        if not condition_name:
            return jsonify({'error': 'Condition name is required'}), 400
        
        # Add medical condition
        condition_id, condition_error = database_service.add_medical_condition(
            user_data['id'],
            condition_name,
            data.get('diagnosis_date'),
            data.get('status', 'active'),
            data.get('notes')
        )
        
        if condition_error:
            return jsonify({'error': condition_error}), 400
        
        return jsonify({
            'message': 'Medical condition added successfully',
            'condition_id': condition_id
        }), 201
        
    except Exception as e:
        print(f"Medical condition add error: {str(e)}")
        return jsonify({'error': 'Failed to add medical condition'}), 500

@app.route('/api/medical-history', methods=['GET'])
@token_required
def get_medical_history():
    """Get medical history for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        history, history_error = database_service.get_medical_history(user_data['id'])
        
        if history_error:
            return jsonify({'error': history_error}), 400
        
        return jsonify({
            'medical_history': history
        }), 200
        
    except Exception as e:
        print(f"Medical history get error: {str(e)}")
        return jsonify({'error': 'Failed to get medical history'}), 500

@app.route('/api/stats', methods=['GET'])
@token_required
def get_user_stats():
    """Get user statistics (admin endpoint)"""
    try:
        stats, error = database_service.get_user_stats()
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify(stats), 200
        
    except Exception as e:
        print(f"Stats get error: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

# Wearable Device API Endpoints

@app.route('/api/devices', methods=['GET'])
@token_required
def get_user_devices():
    """Get all devices linked to current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        devices, device_error = database_service.get_user_devices(user_data['id'])
        
        if device_error:
            return jsonify({'error': device_error}), 400
        
        return jsonify({
            'devices': devices
        }), 200
        
    except Exception as e:
        print(f"Get devices error: {str(e)}")
        return jsonify({'error': 'Failed to get devices'}), 500

@app.route('/api/devices/link', methods=['POST'])
@token_required
def link_device():
    """Link a wearable device to current user"""
    try:
        data = request.get_json()
        device_id = data.get('device_id', '').strip()
        device_name = data.get('device_name', '').strip() or None
        device_type = data.get('device_type', 'ESP32')
        
        if not device_id:
            return jsonify({'error': 'Device ID is required'}), 400
        
        # Validate device ID format (basic validation)
        if len(device_id) < 5:
            return jsonify({'error': 'Device ID must be at least 5 characters'}), 400
        
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        device, link_error = database_service.link_device(
            user_data['id'], 
            device_id, 
            device_name, 
            device_type
        )
        
        if link_error:
            return jsonify({'error': link_error}), 400
        
        return jsonify({
            'message': 'Device linked successfully',
            'device': device
        }), 201
        
    except Exception as e:
        print(f"Link device error: {str(e)}")
        return jsonify({'error': 'Failed to link device'}), 500

@app.route('/api/devices/<device_id>/unlink', methods=['DELETE'])
@token_required
def unlink_device(device_id):
    """Unlink a device from current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        success, unlink_error = database_service.unlink_device(user_data['id'], device_id)
        
        if unlink_error:
            return jsonify({'error': unlink_error}), 400
        
        return jsonify({
            'message': 'Device unlinked successfully'
        }), 200
        
    except Exception as e:
        print(f"Unlink device error: {str(e)}")
        return jsonify({'error': 'Failed to unlink device'}), 500

@app.route('/api/device/info', methods=['GET'])
@token_required
def get_device_info():
    """Get device information for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has a linked device
        if user_data.get('linked_device_id'):
            device_info = {
                'device_id': user_data['linked_device_id'],
                'device_type': 'ESP32',
                'linked_at': user_data.get('device_linked_at')
            }
            
            return jsonify({
                'has_device': True,
                'device_info': device_info
            }), 200
        else:
            return jsonify({
                'has_device': False,
                'message': 'No device linked'
            }), 200
            
    except Exception as e:
        print(f"Get device info error: {str(e)}")
        return jsonify({'error': 'Failed to get device info'}), 500

@app.route('/api/device/link', methods=['POST'])
@token_required
def link_device_simple():
    """Link a wearable device to current user (simple endpoint)"""
    try:
        data = request.get_json()
        device_id = data.get('device_id', '').strip()
        
        if not device_id:
            return jsonify({'error': 'Device ID is required'}), 400
        
        # Validate device ID format (basic validation)
        if len(device_id) < 5:
            return jsonify({'error': 'Device ID must be at least 5 characters'}), 400
        
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Use the existing link_device_to_user method
        result, link_error = database_service.link_device_to_user(user_data['id'], device_id)
        
        if link_error:
            return jsonify({'error': link_error}), 400
        
        return jsonify({
            'message': 'Device linked successfully',
            'device_info': result
        }), 200
        
    except Exception as e:
        print(f"Link device error: {str(e)}")
        return jsonify({'error': 'Failed to link device'}), 500

@app.route('/api/device/unlink', methods=['POST'])
@token_required
def unlink_device_simple():
    """Unlink device from current user (simple endpoint)"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Use the existing unlink_device_from_user method
        result, unlink_error = database_service.unlink_device_from_user(user_data['id'])
        
        if unlink_error:
            return jsonify({'error': unlink_error}), 400
        
        return jsonify({
            'message': 'Device unlinked successfully'
        }), 200
        
    except Exception as e:
        print(f"Unlink device error: {str(e)}")
        return jsonify({'error': 'Failed to unlink device'}), 500

@app.route('/api/device/data', methods=['GET'])
@token_required
def get_device_data():
    """Get device data for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        if not user_data.get('linked_device_id'):
            return jsonify({
                'has_device': False,
                'message': 'No device linked'
            }), 200
        
        hours = request.args.get('hours', 24, type=int)
        
        # Get device data using existing method
        device_data, data_error = database_service.get_device_data_for_user(user_data['id'], hours)
        
        if data_error:
            return jsonify({'error': data_error}), 400
        
        return jsonify({
            'has_device': True,
            'data': device_data
        }), 200
        
    except Exception as e:
        print(f"Get device data error: {str(e)}")
        return jsonify({'error': 'Failed to get device data'}), 500

@app.route('/api/device/data/latest', methods=['GET'])
@token_required
def get_latest_device_data():
    """Get latest device data for current user"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        if not user_data.get('linked_device_id'):
            return jsonify({
                'has_device': False,
                'message': 'No device linked'
            }), 200
        
        # Get latest device data using existing method
        latest_data, data_error = database_service.get_latest_device_data(user_data['id'])
        
        if data_error:
            return jsonify({
                'has_device': True,
                'has_data': False,
                'message': data_error
            }), 200
        
        return jsonify({
            'has_device': True,
            'has_data': True,
            'latest_data': latest_data
        }), 200
        
    except Exception as e:
        print(f"Get latest device data error: {str(e)}")
        return jsonify({'error': 'Failed to get latest device data'}), 500

@app.route('/api/device-data/24h', methods=['GET'])
@token_required
def get_device_data_24h():
    """Get device data for the last 24 hours"""
    try:
        user_data, error = database_service.get_user_by_email(request.current_user)
        
        if error or not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        device_id = request.args.get('device_id')
        
        device_data, data_error = database_service.get_device_data_24h(user_data['id'], device_id)
        
        if data_error:
            return jsonify({'error': data_error}), 400
        
        return jsonify({
            'device_data': device_data,
            'count': len(device_data)
        }), 200
        
    except Exception as e:
        print(f"Get device data error: {str(e)}")
        return jsonify({'error': 'Failed to get device data'}), 500

# Device Data Reception Endpoint (for wearable devices)

@app.route('/device', methods=['POST'])
def receive_device_data():
    """Receive data from wearable devices"""
    try:
        data = request.get_json()
        
        # Validate required fields
        device_id = data.get('device_id')
        timestamp = data.get('timestamp')
        sensor_data = data.get('data', {})
        
        if not device_id:
            return jsonify({'error': 'device_id is required'}), 400
        
        if not timestamp:
            return jsonify({'error': 'timestamp is required'}), 400
        
        # Save device data
        result, error = database_service.save_device_data(device_id, timestamp, sensor_data)
        
        if error:
            if "not linked" in error:
                return jsonify({'error': 'Device not linked to any user'}), 404
            return jsonify({'error': error}), 400
        
        # Broadcast real-time data to connected users
        if result and 'user_id' in result:
            # Find connected sessions for this user
            user_data, user_error = database_service.get_user_by_id(result['user_id'])
            if not user_error and user_data:
                user_email = user_data['email']
                
                # Prepare real-time data payload
                realtime_data = {
                    'device_id': device_id,
                    'timestamp': timestamp,
                    'temperature_c': sensor_data.get('temperature_c'),
                    'heart_rate_bpm': sensor_data.get('heart_rate_bpm'),
                    'spo2_percent': sensor_data.get('spo2_percent'),
                    'ecg_data': sensor_data.get('ecg_mV', [])
                }
                
                # Find user's socket sessions and emit data
                user_sessions_list = [sid for sid, session in user_sessions.items() 
                                    if session.get('user_email') == user_email]
                
                for session_id in user_sessions_list:
                    socketio.emit('device_data_update', realtime_data, room=session_id)
                    print(f"Sent real-time data to user {user_email} (session: {session_id})")
        
        return jsonify({
            'message': 'Data received successfully',
            'device_id': device_id,
            'timestamp': timestamp,
            'data_saved': result
        }), 200
        
    except Exception as e:
        print(f"Device data error: {str(e)}")
        return jsonify({'error': 'Failed to process device data'}), 500



@app.route('/health')
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "system_message": SYSTEM_MESSAGE["content"][:100] + "...",
        "deployment": deployment,
        "endpoint": endpoint
    }

# --- 6. SOCKET.IO EVENT HANDLERS ---

@socketio.on('connect')
def handle_connect(auth):
    session_id = request.sid
    print(f'Client {session_id} attempting to connect...')
    
    # Verify authentication
    token = auth.get('token') if auth else None
    if not token:
        print(f'Connection rejected for {session_id}: No token provided')
        return False
    
    user_email = verify_token(token)
    if not user_email:
        print(f'Connection rejected for {session_id}: Invalid token')
        return False
    
    # Store user info in session
    user_sessions[session_id] = {
        'user_email': user_email,
        'connected_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Initialize conversation history for this user
    if user_email not in user_conversation_histories:
        user_conversation_histories[user_email]['default'] = [SYSTEM_MESSAGE.copy()]
    
    # Get user data from database
    user_data, error = database_service.get_user_by_email(user_email)
    user_name = user_data['name'] if user_data else 'User'
    
    print(f'Client {session_id} connected successfully as {user_email}')
    emit('connection_success', {'message': f'Welcome back, {user_name}!'})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    user_session = user_sessions.get(session_id)
    
    if user_session:
        print(f'Client {session_id} ({user_session["user_email"]}) disconnected.')
        del user_sessions[session_id]
    else:
        print(f'Client {session_id} disconnected.')

@socketio.on('clear_conversation')
def handle_clear_conversation():
    """Clear conversation history for current user"""
    session_id = request.sid
    user_session = user_sessions.get(session_id)
    
    if not user_session:
        emit('error', {'message': 'Authentication required'})
        return
    
    user_email = user_session['user_email']
    
    # Get user data from database
    user_data, user_error = database_service.get_user_by_email(user_email)
    if not user_error and user_data:
        # Clear from database
        deleted_count, db_error = database_service.clear_conversation_history(user_data['id'])
        print(f'Cleared {deleted_count or 0} messages from database for {user_email}')
    
    # Clear from memory
    user_conversation_histories[user_email]['default'] = [SYSTEM_MESSAGE.copy()]
    
    print(f'Cleared conversation history for {user_email}')
    emit('conversation_cleared', {'message': 'Conversation history cleared'})

@socketio.on('user_input')
def handle_user_input(data):
    session_id = request.sid
    user_session = user_sessions.get(session_id)
    
    if not user_session:
        emit('error', {'message': 'Authentication required'})
        return
    
    user_email = user_session['user_email']
    print(f'Received data from {user_email} ({session_id}): {data}')
    
    try:
        # Get user data from database
        user_data, user_error = database_service.get_user_by_email(user_email)
        if user_error or not user_data:
            emit('error', {'message': 'User not found'})
            return
        
        user_id = user_data['id']
        
        # Validate and handle input data
        if isinstance(data, str):
            # Simple text message
            user_content = data.strip()
            message_content = data.strip()
            message_type = 'text'
        elif isinstance(data, dict):
            # Message object with potential attachment
            text = data.get('text', '').strip() if data.get('text') else ''
            attachment = data.get('attachment')
            
            if attachment and isinstance(attachment, dict):
                # Create content array for image + text
                message_content = []
                if text:
                    message_content.append({
                        "type": "text",
                        "text": text
                    })
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": attachment.get('data', '')
                    }
                })
                user_content = f"{text} [Image: {attachment.get('name', 'image')}]" if text else f"[Image: {attachment.get('name', 'image')}]"
                message_type = 'image'
            else:
                message_content = text
                user_content = text
                message_type = 'text'
        else:
            # Invalid data type
            emit('error', {'message': 'Invalid message format'})
            return
        
        # Check if message is empty
        if not user_content or user_content.strip() == '':
            emit('error', {'message': 'Message cannot be empty'})
            return
        
        # Save user message to database
        database_service.save_conversation_message(user_id, 'default', 'user', message_content, message_type)
        
        # Get user's conversation history from database
        conversation_history, history_error = database_service.get_conversation_history(user_id, 'default', 50)
        
        # Build conversation for OpenAI (include system message)
        current_conversation = [SYSTEM_MESSAGE.copy()]
        
        if not history_error and conversation_history:
            for msg in conversation_history:
                if msg['role'] in ['user', 'assistant']:
                    current_conversation.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
        
        # Also use in-memory conversation as fallback
        user_conversations = user_conversation_histories[user_email]
        memory_conversation = user_conversations['default']
        
        # Add user message to memory conversation
        memory_conversation.append({
            "role": "user",
            "content": message_content
        })
        
        # Use the longer conversation (database or memory)
        if len(current_conversation) < len(memory_conversation):
            current_conversation = memory_conversation
        
        print(f'Processing message for {user_email}: {user_content[:100]}{"..." if len(user_content) > 100 else ""}')
        
        # Check if AI client is available
        if client is None:
            bot_reply = "I apologize, but the AI chat functionality is currently unavailable. The healthcare application is running, but the AI service needs to be configured. Please contact your administrator to set up Azure OpenAI credentials."
            print(f'AI client not available, sending fallback response to {user_email}')
        else:
            try:
                # Generate response using Azure OpenAI (with cache busting)
                completion = client.chat.completions.create(
                    model=deployment,
                    messages=current_conversation,
                    max_tokens=800,
                    temperature=0.7,  # Slight randomness to prevent caching
                    top_p=0.95,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=None,
                    stream=False,
                    # Add user identifier to prevent caching
                    user=f"user_{user_email}_{int(__import__('time').time())}"
                )
                
                bot_reply = completion.choices[0].message.content
                print(f'Sending AI response to {user_email}: {bot_reply}')
            except Exception as ai_error:
                bot_reply = "I'm sorry, I'm experiencing technical difficulties right now. Please try again in a moment, or contact support if the problem persists."
                print(f'AI error for {user_email}: {str(ai_error)}')
        
        # Save bot response to database
        database_service.save_conversation_message(user_id, 'default', 'assistant', bot_reply, 'text')
        
        # Add bot response to memory conversation
        memory_conversation.append({
            "role": "assistant",
            "content": bot_reply
        })
        
        # Emit the response back to the client
        emit('bot_response', bot_reply)
        
    except Exception as e:
        error_message = "Sorry, I'm having trouble processing your request. Please try again."
        print(f"Error processing message for user {user_email}: {str(e)}")
        print(f"Data received: {data}")
        import traceback
        traceback.print_exc()
        emit('error', {'message': error_message})

# --- 6. RUN THE APPLICATION ---

if __name__ == '__main__':
    print("🚀 Starting Kare Healthcare Server...")
    print(f"🌐 Server will be available at: http://localhost:5001")
    print(f"🔗 Frontend should connect to: http://localhost:5001")
    print("=" * 50)
    
    try:
        socketio.run(
            app, 
            host='127.0.0.1', 
            port=5001, 
            debug=True, 
            allow_unsafe_werkzeug=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("🔄 Trying fallback configuration...")
        try:
            socketio.run(app, host='127.0.0.1', port=5001, debug=False)
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")
            print("💡 Try running on a different port or check if port 5001 is already in use")