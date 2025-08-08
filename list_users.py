
"""
Script to list all users in the healthcare database
"""

import os
from flask import Flask
from models import db, User

def list_users():
    """List all users in the database"""
    print("👥 Listing all users in the healthcare database...")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_path = os.path.join(basedir, 'HEALTH_CARE-main', 'backend', 'instance', 'healthcare.db')
    
    if not os.path.exists(database_path):
        print("❌ Database not found. Please check the path.")
        return
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'temp-key'
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            users = User.query.all()
            
            if not users:
                print("📭 No users found in the database")
                print("💡 Please register a user account first through the web app")
                return
            
            print(f"📋 Found {len(users)} user(s):")
            print("-" * 50)
            
            for user in users:
                print(f"ID: {user.id}")
                print(f"Email: {user.email}")
                print(f"Name: {user.name}")
                print(f"Created: {user.created_at}")
                print("-" * 50)
                
        except Exception as e:
            print(f"❌ Failed to list users: {str(e)}")

if __name__ == '__main__':
    list_users()