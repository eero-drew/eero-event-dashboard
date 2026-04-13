#!/usr/bin/env python3
"""
MiniRack Dashboard - macOS Local Version
"""
import os
import sys
import json
import requests
import threading
import time
import subprocess
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import logging
import pytz

# Configuration
VERSION = "6.7.8-mobile-local"
LOCAL_DIR = Path.home() / ".minirack"
CONFIG_FILE = LOCAL_DIR / "config.json"
TOKEN_FILE = LOCAL_DIR / ".eero_token"
TEMPLATE_FILE = Path(__file__).parent / "deploy" / "index.html"
DATA_CACHE_FILE = LOCAL_DIR / "data_cache.json"

# Ensure local directory exists
LOCAL_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOCAL_DIR / 'dashboard.log'),
        logging.StreamHandler()
    ]
)

# Flask app
app = Flask(__name__)
CORS(app)

def load_config():
    """Load configuration"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Migrate old single network config to new multi-network format
                if 'network_id' in config and 'networks' not in config:
                    config['networks'] = [{
                        'id': config.get('network_id', '20478317'),
                        'name': 'Primary Network',
                        'email': '',
                        'token': '',
                        'active': True
                    }]
                return config
    except Exception as e:
        logging.error("Config load error: " + str(e))
    
    return {
        "networks": [{
            "id": "20478317",
            "name": "Primary Network", 
            "email": "",
            "token": "",
            "active": True
        }],
        "environment": "development",
        "api_url": "api-user.e2ro.com",
        "timezone": "America/New_York"
    }

def save_config(config):
    """Save configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logging.error("Config save error: " + str(e))
        return False

# Import the rest of the dashboard code from the deploy version
sys.path.insert(0, str(Path(__file__).parent / "deploy"))

# Load the main dashboard functions
exec(open(Path(__file__).parent / "deploy" / "dashboard_minimal.py").read())

# Override the main execution for local development
if __name__ == '__main__':
    print(f"🚀 Starting MiniRack Dashboard {VERSION} (Local macOS)")
    print(f"📁 Config directory: {LOCAL_DIR}")
    print(f"🌐 Dashboard will be available at: http://localhost:3000")
    print("📱 Mobile responsive design enabled")
    print("🔧 Press Ctrl+C to stop")
    
    # Initial cache update
    try:
        update_cache()
        logging.info("Initial cache update complete")
    except Exception as e:
        logging.warning("Initial cache update failed: " + str(e))
    
    app.run(host='127.0.0.1', port=3000, debug=True)
