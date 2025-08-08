"""
SQLAlchemy models for Kare Healthcare Assistant
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Additional health profile fields
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    blood_type = Column(String(10), nullable=True)
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    
    # Emergency contact information
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    
    # Wearable device information
    linked_device_id = Column(String(100), nullable=True, unique=True)
    device_linked_at = Column(DateTime, nullable=True)
    
    # Preferences
    marketing_emails_consent = Column(Boolean, default=False)
    sms_notifications_consent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    vital_signs = relationship('VitalSigns', backref='user', lazy=True, cascade='all, delete-orphan')
    medical_history = relationship('MedicalHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    user_sessions = relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, email, password, name, phone=None, date_of_birth=None, gender=None, **kwargs):
        self.email = email.lower().strip()
        self.name = name.strip()
        self.phone = phone
        self.date_of_birth = date_of_birth
        self.gender = gender
        
        # Additional health profile fields
        self.height = kwargs.get('height')
        self.weight = kwargs.get('weight')
        self.blood_type = kwargs.get('blood_type')
        self.allergies = kwargs.get('allergies')
        self.current_medications = kwargs.get('current_medications')
        self.medical_conditions = kwargs.get('medical_conditions')
        
        # Emergency contact information
        self.emergency_contact_name = kwargs.get('emergency_contact_name')
        self.emergency_contact_relationship = kwargs.get('emergency_contact_relationship')
        self.emergency_contact_phone = kwargs.get('emergency_contact_phone')
        
        # Preferences
        self.marketing_emails_consent = kwargs.get('marketing_emails_consent', False)
        self.sms_notifications_consent = kwargs.get('sms_notifications_consent', False)
        
        self.set_password(password)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'height': self.height,
            'weight': self.weight,
            'blood_type': self.blood_type,
            'allergies': self.allergies,
            'current_medications': self.current_medications,
            'medical_conditions': self.medical_conditions,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_relationship': self.emergency_contact_relationship,
            'emergency_contact_phone': self.emergency_contact_phone,
            'linked_device_id': self.linked_device_id,
            'device_linked_at': self.device_linked_at.isoformat() if self.device_linked_at else None,
            'marketing_emails_consent': self.marketing_emails_consent,
            'sms_notifications_consent': self.sms_notifications_consent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

class UserSession(db.Model):
    """User session model for token management"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(500), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<UserSession {self.user_id}>'

class Conversation(db.Model):
    """Conversation history model"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    conversation_id = Column(String(255), nullable=False, default='default')
    message_role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    message_content = Column(Text, nullable=False)
    message_type = Column(String(50), default='text')  # 'text', 'image', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, user_id, conversation_id, message_role, message_content, message_type='text'):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.message_role = message_role
        self.message_type = message_type
        
        # Handle complex content (lists, dicts)
        if isinstance(message_content, (list, dict)):
            self.message_content = json.dumps(message_content)
        else:
            self.message_content = str(message_content)
    
    def get_content(self):
        """Get message content, parsing JSON if needed"""
        try:
            return json.loads(self.message_content)
        except (json.JSONDecodeError, TypeError):
            return self.message_content
    
    def to_dict(self):
        """Convert conversation message to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'role': self.message_role,
            'content': self.get_content(),
            'type': self.message_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Conversation {self.user_id}:{self.conversation_id}>'

class VitalSigns(db.Model):
    """Vital signs model for health monitoring"""
    __tablename__ = 'vital_signs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    temperature = Column(Float, nullable=True)  # in Fahrenheit
    heart_rate = Column(Integer, nullable=True)  # beats per minute
    blood_pressure_systolic = Column(Integer, nullable=True)  # mmHg
    blood_pressure_diastolic = Column(Integer, nullable=True)  # mmHg
    oxygen_saturation = Column(Integer, nullable=True)  # percentage
    weight = Column(Float, nullable=True)  # in kg
    height = Column(Float, nullable=True)  # in cm
    recorded_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    def to_dict(self):
        """Convert vital signs to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'temperature': self.temperature,
            'heart_rate': self.heart_rate,
            'blood_pressure_systolic': self.blood_pressure_systolic,
            'blood_pressure_diastolic': self.blood_pressure_diastolic,
            'oxygen_saturation': self.oxygen_saturation,
            'weight': self.weight,
            'height': self.height,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'notes': self.notes
        }
    
    @property
    def blood_pressure(self):
        """Get blood pressure as systolic/diastolic string"""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None
    
    def __repr__(self):
        return f'<VitalSigns {self.user_id}:{self.recorded_at}>'

class MedicalHistory(db.Model):
    """Medical history model for tracking conditions"""
    __tablename__ = 'medical_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    condition_name = Column(String(255), nullable=False)
    diagnosis_date = Column(Date, nullable=True)
    status = Column(String(50), default='active')  # 'active', 'resolved', 'chronic'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert medical history to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'condition_name': self.condition_name,
            'diagnosis_date': self.diagnosis_date.isoformat() if self.diagnosis_date else None,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<MedicalHistory {self.user_id}:{self.condition_name}>'

class WearableDevice(db.Model):
    """Wearable device model for tracking user devices"""
    __tablename__ = 'wearable_devices'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(100), default='ESP32')  # ESP32, Arduino, etc.
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device_data = relationship('DeviceData', backref='device', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert wearable device to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<WearableDevice {self.device_id}>'

class DeviceData(db.Model):
    """Device data model for storing wearable sensor readings"""
    __tablename__ = 'device_data'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(255), ForeignKey('wearable_devices.device_id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Vital signs data
    temperature_c = Column(Float, nullable=True)
    temperature_f = Column(Float, nullable=True)
    heart_rate_bpm = Column(Integer, nullable=True)
    spo2_percent = Column(Integer, nullable=True)
    ecg_data = Column(Text, nullable=True)  # JSON string of ECG readings
    
    # Additional sensor data (extensible)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    
    # Metadata
    data_quality = Column(String(50), default='good')  # good, fair, poor
    battery_level = Column(Integer, nullable=True)
    signal_strength = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, device_id, user_id, timestamp, **kwargs):
        self.device_id = device_id
        self.user_id = user_id
        self.timestamp = timestamp
        
        # Set vital signs data
        self.temperature_c = kwargs.get('temperature_c')
        self.temperature_f = kwargs.get('temperature_f')
        self.heart_rate_bpm = kwargs.get('heart_rate_bpm')
        self.spo2_percent = kwargs.get('spo2_percent')
        
        # Handle ECG data (convert list to JSON string)
        ecg_data = kwargs.get('ecg_mV')
        if ecg_data and isinstance(ecg_data, list):
            self.ecg_data = json.dumps(ecg_data)
        elif ecg_data:
            self.ecg_data = str(ecg_data)
        
        # Additional data
        self.blood_pressure_systolic = kwargs.get('blood_pressure_systolic')
        self.blood_pressure_diastolic = kwargs.get('blood_pressure_diastolic')
        self.steps = kwargs.get('steps')
        self.calories_burned = kwargs.get('calories_burned')
        self.data_quality = kwargs.get('data_quality', 'good')
        self.battery_level = kwargs.get('battery_level')
        self.signal_strength = kwargs.get('signal_strength')
    
    def get_ecg_data(self):
        """Get ECG data as list"""
        if self.ecg_data:
            try:
                return json.loads(self.ecg_data)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def to_dict(self):
        """Convert device data to dictionary"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'temperature_c': self.temperature_c,
            'temperature_f': self.temperature_f,
            'heart_rate_bpm': self.heart_rate_bpm,
            'spo2_percent': self.spo2_percent,
            'ecg_data': self.get_ecg_data(),
            'blood_pressure_systolic': self.blood_pressure_systolic,
            'blood_pressure_diastolic': self.blood_pressure_diastolic,
            'steps': self.steps,
            'calories_burned': self.calories_burned,
            'data_quality': self.data_quality,
            'battery_level': self.battery_level,
            'signal_strength': self.signal_strength,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<DeviceData {self.device_id}:{self.timestamp}>'

# Database utility functions
def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")

def get_user_stats():
    """Get database statistics"""
    try:
        total_users = User.query.filter_by(is_active=True).count()
        users_today = User.query.filter(
            User.created_at >= datetime.utcnow().date(),
            User.is_active == True
        ).count()
        
        # Count unique conversations
        total_conversations = db.session.query(
            Conversation.user_id, 
            Conversation.conversation_id
        ).distinct().count()
        
        return {
            'total_users': total_users,
            'users_registered_today': users_today,
            'total_conversations': total_conversations
        }, None
        
    except Exception as e:
        return None, str(e)