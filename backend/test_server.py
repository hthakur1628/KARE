#!/usr/bin/env python3
"""
Basic test server to verify connectivity
"""

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "message": "🏥 Test Server Running!",
        "status": "success",
        "port": "5001"
    })

@app.route('/api/test')
def test():
    return jsonify({"test": "API working"})

if __name__ == '__main__':
    print("🧪 Starting Test Server...")
    print("🌐 Testing connectivity on http://localhost:5001")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    except Exception as e:
        print(f"❌ Port 5001 failed: {e}")
        try:
            print("🔄 Trying port 8080...")
            app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
        except Exception as e2:
            print(f"❌ Port 8080 failed: {e2}")
            print("💡 Try running as administrator or check Windows Firewall")