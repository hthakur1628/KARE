# Kare Healthcare System

A comprehensive healthcare management system with real-time vital signs monitoring, patient management, and AI-powered chat assistance.

## 🏗️ Project Structure
                                                                  
```
HEALTH_CARE-main/
├── backend/                    # Flask backend server
│   ├── app.py                 # Main Flask application
│   ├── models.py              # Database models
│   ├── database_service.py    # Database operations
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── instance/             # Database files (SQLite)
├── frontend/                  # Static web frontend
│   ├── assets/
│   │   ├── css/              # Stylesheets
│   │   ├── js/               # JavaScript files
│   │   └── images/           # Static images
│   ├── index.html            # Landing page
│   ├── login.html            # Authentication
│   ├── signup.html           # User registration
│   ├── profile.html          # User profile management
│   ├── vital.html            # Vital signs dashboard
│   └── chat.html             # AI chat interface
├── .env                      # Environment configuration
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🚀 Features

### 📊 Vital Signs Monitoring
- Real-time heart rate, SpO2, and temperature tracking
- ESP32 device integration
- Interactive charts and historical data
- WebSocket-based live updates

### 👤 User Management
- Secure user registration and authentication
- Comprehensive profile management
- Medical history tracking
- Emergency contact information

### 💬 AI Chat Assistant
- OpenAI-powered health consultations
- Medical advice and information
- Symptom analysis and recommendations

### 🔐 Security
- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Input validation and sanitization

## 🛠️ Setup Instructions

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv healthcare_env
   healthcare_env\Scripts\activate  # Windows
   # or
   source healthcare_env/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the server:**
   ```bash
   python app.py
   ```

### Frontend Setup

1. **Serve static files:**
   - Use a local web server (e.g., Live Server in VS Code)
   - Or use Python's built-in server:
     ```bash
     cd frontend
     python -m http.server 8000
     ```

2. **Access the application:**
   - Frontend: `http://localhost:8000`
   - Backend API: `http://localhost:5001`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory with:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///instance/healthcare.db

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Azure (if using)
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=your-azure-tenant-id
```

### Database Setup

The application uses SQLite by default. You can initialize the database using the provided scripts:

#### Quick Setup (Windows):
```bash
cd backend
manage_db.bat init
```

#### Quick Setup (Linux/Mac):
```bash
cd backend
./manage_db.sh init
```

#### Manual Setup:
```bash
cd backend
python init_database.py --sample-data
```

This will create the database with sample users and test data.

## 📱 Device Integration

### ESP32 Setup

1. **Device Registration:**
   - Each ESP32 device needs a unique device ID
   - Users link devices through the vital signs dashboard

2. **Data Format:**
   - Heart rate (BPM)
   - SpO2 percentage
   - Temperature (Celsius)
   - Timestamp

3. **Communication:**
   - HTTP POST requests to `/api/device/data`
   - WebSocket connections for real-time updates

## 🧪 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### User Management
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update user profile

### Device Management
- `POST /api/device/link` - Link device to user
- `POST /api/device/unlink` - Unlink device
- `GET /api/device/info` - Get device information
- `GET /api/device/data` - Get device data
- `POST /api/device/data` - Submit device data

### Chat
- `POST /api/chat/message` - Send chat message
- `GET /api/chat/history` - Get chat history

## 💾 Database Management

### Database Scripts

The project includes several scripts for database management:

#### Windows Users:
```bash
# Initialize database with sample data
manage_db.bat init

# Create backup
manage_db.bat backup

# List available backups
manage_db.bat list

# Restore from backup
manage_db.bat restore

# Reset database (delete all data)
manage_db.bat reset

# Verify database integrity
manage_db.bat verify
```

#### Linux/Mac Users:
```bash
# Initialize database with sample data
./manage_db.sh init

# Create backup
./manage_db.sh backup

# List available backups
./manage_db.sh list

# Restore from backup
./manage_db.sh restore

# Reset database (delete all data)
./manage_db.sh reset

# Verify database integrity
./manage_db.sh verify
```

#### Manual Database Operations:
```bash
# Initialize with sample data
python init_database.py --sample-data

# Reset database (drop and recreate)
python init_database.py --reset --sample-data

# Verify existing database
python init_database.py --verify-only

# Create backup
python backup_database.py backup

# Restore from backup
python backup_database.py restore --input backup_file.db

# List backups
python backup_database.py list-backups
```

### Sample Login Credentials

After running the initialization script, you can use these test accounts:

**User Account:**
- Email: `john.doe@example.com`
- Password: `password123`
- Device ID: `13554`

**Admin Account:**
- Email: `admin@healthcare.com`
- Password: `admin123`
- Device ID: `13556`

## 🔍 Troubleshooting

### Common Issues

1. **Token Expired:**
   - Log out and log back in to refresh authentication token

2. **Device Not Linking:**
   - Check device ID format
   - Ensure device is powered and connected
   - Verify backend server is running

3. **Charts Not Loading:**
   - Check browser console for JavaScript errors
   - Ensure Chart.js libraries are loaded

4. **WebSocket Connection Failed:**
   - Verify backend server is running on correct port
   - Check CORS configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions, please contact the development team or create an issue in the repository.