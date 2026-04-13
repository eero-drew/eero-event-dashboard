#!/usr/bin/env python3
"""
MiniRack Dashboard - macOS Local Setup
Sets up the dashboard to run locally on macOS
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python 3.8+ is available"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print("Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")
    
    requirements = [
        "flask==2.3.3",
        "flask-cors==4.0.0", 
        "requests==2.31.0",
        "pytz==2023.3"
    ]
    
    try:
        for req in requirements:
            print(f"Installing {req}...")
            subprocess.run([sys.executable, "-m", "pip", "install", req], 
                         check=True, capture_output=True)
        print("✅ All dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_local_config():
    """Create local configuration directory and files"""
    print("📁 Creating local configuration...")
    
    # Create local directories
    local_dir = Path.home() / ".minirack"
    local_dir.mkdir(exist_ok=True)
    
    config_file = local_dir / "config.json"
    
    # Default configuration
    config = {
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
    
    if not config_file.exists():
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Created config file: {config_file}")
    else:
        print(f"✅ Config file exists: {config_file}")
    
    return str(local_dir)

def create_local_dashboard():
    """Create local dashboard script"""
    print("🐍 Creating local dashboard script...")
    
    dashboard_content = '''#!/usr/bin/env python3
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
'''
    
    with open("dashboard_local.py", 'w') as f:
        f.write(dashboard_content)
    
    # Make executable
    os.chmod("dashboard_local.py", 0o755)
    print("✅ Created dashboard_local.py")

def create_run_script():
    """Create convenient run script"""
    print("📜 Creating run script...")
    
    run_script = '''#!/bin/bash
# MiniRack Dashboard - macOS Local Runner

echo "🚀 Starting MiniRack Dashboard (Local macOS)"
echo "📱 Mobile responsive design enabled"
echo "🌐 Dashboard: http://localhost:3000"
echo "🔧 Press Ctrl+C to stop"
echo ""

# Check if Python dependencies are installed
python3 -c "import flask, flask_cors, requests, pytz" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Run: python3 setup_macos_local.py"
    exit 1
fi

# Run the dashboard
python3 dashboard_local.py
'''
    
    with open("run_local.sh", 'w') as f:
        f.write(run_script)
    
    os.chmod("run_local.sh", 0o755)
    print("✅ Created run_local.sh")

def main():
    """Main setup function"""
    print("🍎 MiniRack Dashboard - macOS Local Setup")
    print("=" * 50)
    
    if not check_python_version():
        return False
    
    if not install_dependencies():
        return False
    
    local_dir = create_local_config()
    create_local_dashboard()
    create_run_script()
    
    print("\n🎉 Setup complete!")
    print("=" * 50)
    print("📁 Configuration directory:", local_dir)
    print("🚀 To start the dashboard:")
    print("   ./run_local.sh")
    print("   OR")
    print("   python3 dashboard_local.py")
    print("")
    print("🌐 Dashboard URL: http://localhost:3000")
    print("🔧 Admin panel: Click the π button")
    print("📱 Mobile responsive design included")
    print("")
    print("⚙️  Configuration:")
    print(f"   Config file: {local_dir}/config.json")
    print(f"   Logs: {local_dir}/dashboard.log")
    print(f"   Cache: {local_dir}/data_cache.json")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)