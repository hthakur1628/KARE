#!/usr/bin/env python3
"""
Simple Database Initialization Script

Run this file to create healthcare.db with all required tables.
No sample data - just empty tables ready for use.

Usage: python db_init.py
"""

import os
from flask import Flask
from models import db

def main():
    """Create empty healthcare database"""
    print("🏥 Creating healthcare.db database...")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_path = os.path.join(basedir, 'instance', 'healthcare.db')
    
    # Ensure instance directory exists
    instance_dir = os.path.dirname(database_path)
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"✅ Created directory: {instance_dir}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'temp-key'
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print(f"✅ Database created: {database_path}")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        print("\n🎉 Database is ready!")
        print("   You can now start your Flask server.")

if __name__ == '__main__':
    main()