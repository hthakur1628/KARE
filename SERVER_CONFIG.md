# KARE Healthcare Server Configuration

## Updated Configuration (Fixed Connection Issues)

### Server Settings
- **Host**: `0.0.0.0` (accessible from all network interfaces)
- **Port**: `3001` (changed from 5001 to avoid conflicts)
- **Frontend URL**: `http://localhost:3001`
- **API Base URL**: `http://localhost:3001/api`

### Files Updated
1. **Backend Files**:
   - `backend/app.py` - Changed port from 5001 to 3001, host from 127.0.0.1 to 0.0.0.0
   - `backend/start_server.py` - Updated port configuration

2. **Frontend Files**:
   - `frontend/assets/js/vital_simple.js` - Updated API_BASE to port 3001
   - `frontend/assets/js/vital.js` - Updated API_BASE and Socket.IO connection to port 3001
   - `frontend/assets/js/signup.js` - Updated API_BASE to port 3001
   - `frontend/assets/js/chat.js` - Updated Socket.IO connection to port 3001
   - `frontend/login.html` - Updated API_BASE to port 3001
   - `frontend/forgot-password.html` - Updated API_BASE to port 3001
   - `frontend/test_frontend_chat.html` - Updated API and Socket.IO URLs to port 3001

3. **ESP8266 File**:
   - `esp8266_temperature_sensor.ino` - Updated server URL to use port 3001 and network IP

### How to Start the Server

#### Option 1: Using Batch File (Windows)
```bash
# Double-click or run:
start_server.bat
```

#### Option 2: Manual Start
```bash
cd backend
python start_server.py
```

#### Option 3: Direct Python
```bash
cd backend
python app.py
```

### Network Configuration
- Server now binds to `0.0.0.0:3001` making it accessible from:
  - Local machine: `http://localhost:3001`
  - Network devices: `http://[YOUR_IP]:3001`
  - ESP8266 devices: `http://192.168.1.100:3001` (update IP as needed)

### ESP8266 Configuration
Update the ESP8266 code with your actual network IP address:
```cpp
const char* serverURL = "http://[YOUR_ACTUAL_IP]:3001/device";
```

### Troubleshooting
1. If port 3001 is in use, the server will try port 3002
2. Check firewall settings if external devices can't connect
3. Update ESP8266 IP address to match your network configuration
4. Ensure all frontend files are using the same port (3001)

### Testing Connection
1. Start the server using one of the methods above
2. Open browser to `http://localhost:3001`
3. Check browser console for connection status
4. Test API endpoints at `http://localhost:3001/api/`