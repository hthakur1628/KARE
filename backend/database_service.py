"""
Database service layer using SQLAlchemy for Kare Healthcare Assistant
"""

from models import db, User, UserSession, Conversation, VitalSigns, MedicalHistory, WearableDevice, DeviceData
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, and_, func
from datetime import datetime, date, timedelta
import json

class DatabaseService:
    """Service class for database operations using SQLAlchemy"""
    
    # User management methods
    @staticmethod
    def create_user(email, password, name, phone=None, date_of_birth=None, gender=None, **kwargs):
        """Create a new user with comprehensive health profile"""
        try:
            # Parse date_of_birth if it's a string
            if isinstance(date_of_birth, str):
                try:
                    date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    date_of_birth = None
            
            # Extract health profile data from kwargs
            health_profile = {}
            
            # Handle metadata if provided
            metadata = kwargs.get('metadata', {})
            if metadata:
                # Extract health information
                health_profile.update({
                    'height': metadata.get('height'),
                    'weight': metadata.get('weight'),
                    'blood_type': metadata.get('blood_type'),
                    'allergies': metadata.get('allergies'),
                    'current_medications': metadata.get('medications'),
                    'medical_conditions': metadata.get('medical_conditions')
                })
                
                # Extract emergency contact
                emergency_contact = metadata.get('emergency_contact', {})
                if emergency_contact:
                    health_profile.update({
                        'emergency_contact_name': emergency_contact.get('name'),
                        'emergency_contact_relationship': emergency_contact.get('relationship'),
                        'emergency_contact_phone': emergency_contact.get('phone')
                    })
                
                # Extract preferences
                preferences = metadata.get('preferences', {})
                if preferences:
                    health_profile.update({
                        'marketing_emails_consent': preferences.get('marketing_emails', False),
                        'sms_notifications_consent': preferences.get('sms_notifications', False)
                    })
            
            # Also handle direct kwargs (for backward compatibility)
            for key in ['height', 'weight', 'blood_type', 'allergies', 'current_medications', 
                       'medical_conditions', 'emergency_contact_name', 'emergency_contact_relationship',
                       'emergency_contact_phone', 'marketing_emails_consent', 'sms_notifications_consent']:
                if key in kwargs:
                    health_profile[key] = kwargs[key]
            
            user = User(
                email=email,
                password=password,
                name=name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
                **health_profile
            )
            
            db.session.add(user)
            db.session.commit()
            
            return user.to_dict(), None
            
        except IntegrityError:
            db.session.rollback()
            return None, "User already exists"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user with email and password"""
        try:
            user = User.query.filter_by(email=email.lower().strip(), is_active=True).first()
            
            if not user or not user.check_password(password):
                return None, "Invalid credentials"
            
            return user.to_dict(), None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        try:
            user = User.query.filter_by(email=email.lower().strip(), is_active=True).first()
            
            if user:
                return user.to_dict(), None
            return None, "User not found"
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            
            if user:
                return user.to_dict(), None
            return None, "User not found"
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """Update user information"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            
            if not user:
                return None, "User not found"
            
            # Update allowed fields
            allowed_fields = ['name', 'phone', 'date_of_birth', 'gender', 'email']
            updated = False
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    if field == 'date_of_birth' and isinstance(value, str):
                        try:
                            value = datetime.strptime(value, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    elif field == 'email':
                        # Validate email format and check for uniqueness
                        value = value.lower().strip()
                        if not value or '@' not in value:
                            continue
                        
                        # Check if email is already taken by another user
                        existing_user = User.query.filter_by(email=value, is_active=True).first()
                        if existing_user and existing_user.id != user_id:
                            return None, "Email address is already in use"
                    
                    setattr(user, field, value)
                    updated = True
            
            if updated:
                user.updated_at = datetime.utcnow()
                db.session.commit()
                return user.to_dict(), None
            
            return None, "No valid fields to update"
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def update_user_password(user_id, new_password):
        """Update user password"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            
            if not user:
                return False, "User not found"
            
            # Update password
            user.set_password(new_password)
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def link_device_to_user(user_id, device_id):
        """Link a wearable device to a user"""
        try:
            # Check if device is already linked to another user
            existing_user = User.query.filter_by(linked_device_id=device_id, is_active=True).first()
            if existing_user and existing_user.id != user_id:
                return None, "Device is already linked to another user"
            
            # Get the user
            user = User.query.filter_by(id=user_id, is_active=True).first()
            if not user:
                return None, "User not found"
            
            # Link device to user
            user.linked_device_id = device_id
            user.device_linked_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'device_id': device_id,
                'device_type': 'ESP32',
                'linked_at': user.device_linked_at.isoformat()
            }, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def unlink_device_from_user(user_id):
        """Unlink a wearable device from a user"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            if not user:
                return None, "User not found"
            
            if not user.linked_device_id:
                return None, "No device linked to this user"
            
            user.linked_device_id = None
            user.device_linked_at = None
            
            db.session.commit()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def get_user_device_info(user_id):
        """Get device information for a user"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            if not user:
                return None, "User not found"
            
            if not user.linked_device_id:
                return None, "No device linked"
            
            return {
                'device_id': user.linked_device_id,
                'device_type': 'ESP32',
                'linked_at': user.device_linked_at.isoformat() if user.device_linked_at else None
            }, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_latest_device_data(user_id):
        """Get the most recent device data for a user"""
        try:
            # Get user's linked device
            device = WearableDevice.query.filter_by(user_id=user_id, is_active=True).first()
            if not device:
                return None, "No device linked"
            
            # Get latest device data
            latest_data = DeviceData.query.filter_by(
                device_id=device.device_id,
                user_id=user_id
            ).order_by(DeviceData.timestamp.desc()).first()
            
            if not latest_data:
                return None, "No device data found"
            
            return {
                'device_id': latest_data.device_id,
                'timestamp': latest_data.timestamp.isoformat() if latest_data.timestamp else None,
                'temperature_c': latest_data.temperature_c,
                'temperature_f': latest_data.temperature_f,
                'heart_rate_bpm': latest_data.heart_rate_bpm,
                'spo2_percent': latest_data.spo2_percent,
                'ecg_data': latest_data.get_ecg_data()
            }, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_device_data_for_user(user_id, hours=24):
        """Get device data for a user for the last N hours"""
        try:
            # Get user's linked device
            device = WearableDevice.query.filter_by(user_id=user_id, is_active=True).first()
            if not device:
                return None, "No device linked"
            
            # Calculate time range
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            # Get device data for the specified time range
            device_data = DeviceData.query.filter(
                DeviceData.device_id == device.device_id,
                DeviceData.user_id == user_id,
                DeviceData.timestamp >= time_threshold
            ).order_by(DeviceData.timestamp.asc()).all()
            
            # Format data for charts
            timestamps = []
            heart_rate = []
            spo2 = []
            temperature = []
            temperature_f = []
            ecg_data = []
            
            for data in device_data:
                timestamps.append(data.timestamp.isoformat() if data.timestamp else None)
                heart_rate.append(data.heart_rate_bpm if data.heart_rate_bpm else 0)
                spo2.append(data.spo2_percent if data.spo2_percent else 0)
                temperature.append(data.temperature_c if data.temperature_c else 0)
                temperature_f.append(data.temperature_f if data.temperature_f else 0)
                ecg_data.append(data.get_ecg_data())
            
            return {
                'timestamps': timestamps,
                'heart_rate': heart_rate,
                'spo2': spo2,
                'temperature': temperature_f,  # Use Fahrenheit for frontend display
                'temperature_c': temperature,
                'temperature_f': temperature_f,
                'ecg_data': ecg_data
            }, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_device_data_24h(user_id, device_id=None):
        """Get device data for the last 24 hours"""
        try:
            # Get user's linked device
            device = WearableDevice.query.filter_by(user_id=user_id, is_active=True).first()
            if not device:
                return None, "No device linked"
            
            # Use provided device_id or user's linked device
            target_device_id = device_id if device_id else device.device_id
            
            # Calculate 24 hours ago
            time_threshold = datetime.utcnow() - timedelta(hours=24)
            
            # Get device data for the last 24 hours
            device_data = DeviceData.query.filter(
                DeviceData.device_id == target_device_id,
                DeviceData.user_id == user_id,
                DeviceData.timestamp >= time_threshold
            ).order_by(DeviceData.timestamp.asc()).all()
            
            # Convert to list of dictionaries
            data_list = []
            for data in device_data:
                data_list.append({
                    'id': data.id,
                    'device_id': data.device_id,
                    'timestamp': data.timestamp.isoformat() if data.timestamp else None,
                    'temperature_c': data.temperature_c,
                    'temperature_f': data.temperature_f,
                    'heart_rate_bpm': data.heart_rate_bpm,
                    'spo2_percent': data.spo2_percent,
                    'ecg_data': data.get_ecg_data()
                })
            
            return data_list, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def save_device_data(device_id, timestamp, sensor_data):
        """Save device data from wearable devices"""
        try:
            # Check if device exists and is linked to a user
            device = WearableDevice.query.filter_by(device_id=device_id).first()
            
            if not device:
                return None, f"Device {device_id} not linked to any user"
            
            # Parse timestamp
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    timestamp = datetime.utcnow()
            
            # Create device data record
            device_data = DeviceData(
                device_id=device.device_id,
                user_id=device.user_id,
                timestamp=timestamp,
                temperature_c=sensor_data.get('temperature_c'),
                temperature_f=sensor_data.get('temperature_f'),
                heart_rate_bpm=sensor_data.get('heart_rate_bpm'),
                spo2_percent=sensor_data.get('spo2_percent'),
                ecg_mV=sensor_data.get('ecg_mV', [])
            )
            
            db.session.add(device_data)
            db.session.commit()
            
            return {
                'id': device_data.id,
                'user_id': device.user_id,
                'device_id': device_id,
                'timestamp': timestamp.isoformat()
            }, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    # Conversation management methods
    @staticmethod
    def save_conversation_message(user_id, conversation_id, role, content, message_type='text'):
        """Save a conversation message"""
        try:
            # Convert content to string if it's not already
            if isinstance(content, (list, dict)):
                content = json.dumps(content)
            
            conversation = Conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_type=message_type
            )
            
            db.session.add(conversation)
            db.session.commit()
            
            return conversation.id, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def get_conversation_history(user_id, conversation_id='default', limit=50):
        """Get conversation history for a user"""
        try:
            conversations = Conversation.query.filter_by(
                user_id=user_id,
                conversation_id=conversation_id
            ).order_by(Conversation.created_at.desc()).limit(limit).all()
            
            # Reverse to get chronological order
            conversations = list(reversed(conversations))
            
            history = []
            for conv in conversations:
                # Try to parse JSON content, fallback to string
                content = conv.content
                try:
                    if isinstance(content, str) and (content.startswith('[') or content.startswith('{')):
                        content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                history.append({
                    'id': conv.id,
                    'role': conv.role,
                    'content': content,
                    'message_type': conv.message_type,
                    'created_at': conv.created_at.isoformat() if conv.created_at else None
                })
            
            return history, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def clear_conversation_history(user_id, conversation_id='default'):
        """Clear conversation history for a user"""
        try:
            deleted_count = Conversation.query.filter_by(
                user_id=user_id,
                conversation_id=conversation_id
            ).delete()
            
            db.session.commit()
            return deleted_count, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def get_conversation_count(user_id):
        """Get total conversation count for a user"""
        try:
            count = Conversation.query.filter_by(user_id=user_id).count()
            return count, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_recent_conversations(user_id, limit=5):
        """Get recent conversations for a user"""
        try:
            conversations = Conversation.query.filter_by(
                user_id=user_id
            ).order_by(Conversation.created_at.desc()).limit(limit).all()
            
            recent = []
            for conv in conversations:
                recent.append({
                    'id': conv.id,
                    'conversation_id': conv.conversation_id,
                    'role': conv.role,
                    'content': conv.content[:100] + '...' if len(conv.content) > 100 else conv.content,
                    'created_at': conv.created_at.isoformat() if conv.created_at else None
                })
            
            return recent, None
            
        except Exception as e:
            return None, str(e)
    
    # Vital signs management methods
    @staticmethod
    def save_vital_signs(user_id, temperature=None, heart_rate=None, blood_pressure_systolic=None, 
                        blood_pressure_diastolic=None, oxygen_saturation=None, weight=None, 
                        height=None, notes=None):
        """Save vital signs for a user"""
        try:
            vital_signs = VitalSigns(
                user_id=user_id,
                temperature=temperature,
                heart_rate=heart_rate,
                blood_pressure_systolic=blood_pressure_systolic,
                blood_pressure_diastolic=blood_pressure_diastolic,
                oxygen_saturation=oxygen_saturation,
                weight=weight,
                height=height,
                notes=notes
            )
            
            db.session.add(vital_signs)
            db.session.commit()
            
            return vital_signs.id, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def get_vital_signs_history(user_id, limit=10):
        """Get vital signs history for a user"""
        try:
            vital_signs = VitalSigns.query.filter_by(
                user_id=user_id
            ).order_by(VitalSigns.recorded_at.desc()).limit(limit).all()
            
            history = []
            for vs in vital_signs:
                history.append({
                    'id': vs.id,
                    'temperature': vs.temperature,
                    'heart_rate': vs.heart_rate,
                    'blood_pressure_systolic': vs.blood_pressure_systolic,
                    'blood_pressure_diastolic': vs.blood_pressure_diastolic,
                    'oxygen_saturation': vs.oxygen_saturation,
                    'weight': vs.weight,
                    'height': vs.height,
                    'notes': vs.notes,
                    'recorded_at': vs.recorded_at.isoformat() if vs.recorded_at else None
                })
            
            return history, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_latest_vital_signs(user_id):
        """Get latest vital signs for a user"""
        try:
            vital_signs = VitalSigns.query.filter_by(
                user_id=user_id
            ).order_by(VitalSigns.recorded_at.desc()).first()
            
            if not vital_signs:
                return None, "No vital signs found"
            
            return {
                'id': vital_signs.id,
                'temperature': vital_signs.temperature,
                'heart_rate': vital_signs.heart_rate,
                'blood_pressure_systolic': vital_signs.blood_pressure_systolic,
                'blood_pressure_diastolic': vital_signs.blood_pressure_diastolic,
                'oxygen_saturation': vital_signs.oxygen_saturation,
                'weight': vital_signs.weight,
                'height': vital_signs.height,
                'notes': vital_signs.notes,
                'recorded_at': vital_signs.recorded_at.isoformat() if vital_signs.recorded_at else None
            }, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_vital_signs_count(user_id):
        """Get total vital signs count for a user"""
        try:
            count = VitalSigns.query.filter_by(user_id=user_id).count()
            return count, None
            
        except Exception as e:
            return None, str(e)
    
    # Medical history management methods
    @staticmethod
    def add_medical_condition(user_id, condition_name, diagnosis_date=None, status='active', notes=None):
        """Add a medical condition to user's history"""
        try:
            # Parse diagnosis_date if it's a string
            if isinstance(diagnosis_date, str):
                try:
                    diagnosis_date = datetime.strptime(diagnosis_date, '%Y-%m-%d').date()
                except ValueError:
                    diagnosis_date = None
            
            medical_history = MedicalHistory(
                user_id=user_id,
                condition_name=condition_name,
                diagnosis_date=diagnosis_date,
                status=status,
                notes=notes
            )
            
            db.session.add(medical_history)
            db.session.commit()
            
            return medical_history.id, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def get_medical_history(user_id):
        """Get medical history for a user"""
        try:
            medical_history = MedicalHistory.query.filter_by(
                user_id=user_id
            ).order_by(MedicalHistory.diagnosis_date.desc()).all()
            
            history = []
            for mh in medical_history:
                history.append({
                    'id': mh.id,
                    'condition_name': mh.condition_name,
                    'diagnosis_date': mh.diagnosis_date.isoformat() if mh.diagnosis_date else None,
                    'status': mh.status,
                    'notes': mh.notes,
                    'created_at': mh.created_at.isoformat() if mh.created_at else None
                })
            
            return history, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_medical_history_count(user_id):
        """Get total medical history count for a user"""
        try:
            count = MedicalHistory.query.filter_by(user_id=user_id).count()
            return count, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def update_user_profile(user_id, name=None, phone=None, date_of_birth=None, gender=None, metadata=None):
        """Update user profile with comprehensive information"""
        try:
            user = User.query.filter_by(id=user_id, is_active=True).first()
            
            if not user:
                return None, "User not found"
            
            # Update basic information
            if name is not None:
                user.name = name
            if phone is not None:
                user.phone = phone
            if date_of_birth is not None:
                if isinstance(date_of_birth, str):
                    try:
                        date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    except ValueError:
                        date_of_birth = None
                user.date_of_birth = date_of_birth
            if gender is not None:
                user.gender = gender
            
            # Update health profile from metadata
            if metadata:
                health_info = metadata.get('health', {})
                if health_info:
                    if 'height' in health_info:
                        user.height = health_info['height']
                    if 'weight' in health_info:
                        user.weight = health_info['weight']
                    if 'blood_type' in health_info:
                        user.blood_type = health_info['blood_type']
                    if 'allergies' in health_info:
                        user.allergies = health_info['allergies']
                    if 'medications' in health_info:
                        user.current_medications = health_info['medications']
                    if 'medical_conditions' in health_info:
                        user.medical_conditions = health_info['medical_conditions']
                
                # Update emergency contact
                emergency_contact = metadata.get('emergency_contact', {})
                if emergency_contact:
                    user.emergency_contact_name = emergency_contact.get('name')
                    user.emergency_contact_relationship = emergency_contact.get('relationship')
                    user.emergency_contact_phone = emergency_contact.get('phone')
                
                # Update preferences
                preferences = metadata.get('preferences', {})
                if preferences:
                    user.marketing_emails_consent = preferences.get('marketing_emails', user.marketing_emails_consent)
                    user.sms_notifications_consent = preferences.get('sms_notifications', user.sms_notifications_consent)
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return user.to_dict(), None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)

# Create database service instance
database_service = DatabaseService()