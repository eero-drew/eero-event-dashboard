#!/usr/bin/env python3
"""
MiniRack Dashboard - Production Ready (Minimal)
Serves the full macOS replica dashboard from external template
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
import logging

# Configuration
VERSION = "6.1.2-production"
CONFIG_FILE = "/opt/eero/app/config.json"
TOKEN_FILE = "/opt/eero/app/.eero_token"
TEMPLATE_FILE = "/opt/eero/app/index.html"
HISTORY_FILE = "/opt/eero/app/device_history.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/eero/logs/dashboard.log'),
        logging.StreamHandler()
    ]
)

# Flask app
app = Flask(__name__)
CORS(app)

def load_config():
    """Load configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Config load error: {e}")
    
    return {
        "network_id": "20478317",
        "environment": "production",
        "api_url": "api-user.e2ro.com"
    }

def load_history():
    """Load historical data from persistent storage"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                logging.info(f"Loaded history: {len(history.get('connected_users', []))} user entries, {len(history.get('signal_strength_avg', []))} signal entries")
                return history
    except Exception as e:
        logging.error(f"History load error: {e}")
    
    return {
        'connected_users': [],
        'signal_strength_avg': []
    }

def save_history(history_data):
    """Save historical data to persistent storage"""
    try:
        # Only save the time-series data, not current device states
        to_save = {
            'connected_users': history_data.get('connected_users', []),
            'signal_strength_avg': history_data.get('signal_strength_avg', [])
        }
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(to_save, f, indent=2)
        os.chmod(HISTORY_FILE, 0o600)
        logging.info(f"Saved history: {len(to_save['connected_users'])} user entries, {len(to_save['signal_strength_avg'])} signal entries")
        return True
    except Exception as e:
        logging.error(f"History save error: {e}")
        return False

def save_config(config):
    """Save configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        logging.error(f"Config save error: {e}")
        return False
        os.chmod(HISTORY_FILE, 0o600)
        logging.info(f"Saved history: {len(to_save['connected_users'])} user entries, {len(to_save['signal_strength_avg'])} signal entries")
        return True
    except Exception as e:
        logging.error(f"History save error: {e}")
        return False
    """Save configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        logging.error(f"Config save error: {e}")
        return False

class EeroAPI:
    def __init__(self):
        self.session = requests.Session()
        self.config = load_config()
        self.api_token = self.load_token()
        self.network_id = self.config.get('network_id', '20478317')
        self.api_url = self.config.get('api_url', 'api-user.e2ro.com')
        self.api_base = f"https://{self.api_url}/2.2"
    
    def load_token(self):
        """Load API token"""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logging.error(f"Token load error: {e}")
        return None
    
    def get_headers(self):
        """Get request headers"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'MiniRack-Dashboard/{VERSION}'
        }
        if self.api_token:
            headers['X-User-Token'] = self.api_token
        return headers
    
    def get_network_info(self):
        """Get network information including name"""
        try:
            url = f"{self.api_base}/networks/{self.network_id}"
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                network_data = data['data']
                logging.info(f"Retrieved network info: {network_data.get('name', 'Unknown')}")
                return network_data
            return {}
        except Exception as e:
            logging.error(f"Network info fetch error: {e}")
            return {}
    
    def get_all_devices(self):
        """Get all devices with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.api_base}/networks/{self.network_id}/devices"
                response = self.session.get(url, headers=self.get_headers(), timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if 'data' in data:
                    devices = data['data'] if isinstance(data['data'], list) else data['data'].get('devices', [])
                    logging.info(f"Retrieved {len(devices)} devices (attempt {attempt + 1})")
                    return devices
                
                logging.warning(f"No data in response (attempt {attempt + 1}): {data}")
                return []
                
            except requests.exceptions.Timeout:
                logging.warning(f"API timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except requests.exceptions.RequestException as e:
                logging.warning(f"API request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except Exception as e:
                logging.error(f"Device fetch error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        logging.error("All device fetch attempts failed")
        return []

# Initialize API
eero_api = EeroAPI()

# Load historical data on startup
historical_data = load_history()

# Data cache - initialize with loaded history
data_cache = {
    'connected_users': historical_data.get('connected_users', []),
    'device_os': {},
    'frequency_distribution': {},
    'signal_strength_avg': historical_data.get('signal_strength_avg', []),
    'devices': [],
    'last_update': None
}

def detect_device_os(device):
    """Detect device OS from manufacturer and hostname"""
    manufacturer = str(device.get('manufacturer', '')).lower()
    hostname = str(device.get('hostname', '')).lower()
    text = f"{manufacturer} {hostname}"
    
    # Amazon detection (prioritize manufacturer field)
    if any(k in manufacturer for k in ['amazon', 'amazon technologies']):
        return 'Amazon'
    elif any(k in text for k in ['echo', 'alexa', 'fire tv', 'kindle']):
        return 'Amazon'
    
    # Apple/iOS detection
    elif any(k in manufacturer for k in ['apple', 'apple inc']):
        return 'iOS'
    elif any(k in text for k in ['iphone', 'ipad', 'mac', 'ios', 'apple']):
        return 'iOS'
    
    # Android detection (includes many manufacturers)
    elif any(k in manufacturer for k in ['samsung', 'google', 'lg electronics', 'htc', 'sony', 'motorola', 'huawei', 'xiaomi', 'oneplus']):
        return 'Android'
    elif any(k in text for k in ['android', 'pixel', 'galaxy']):
        return 'Android'
    
    # Windows detection
    elif any(k in manufacturer for k in ['microsoft', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'msi']):
        return 'Windows'
    elif any(k in text for k in ['windows', 'microsoft', 'surface']):
        return 'Windows'
    
    # Gaming consoles and other specific devices
    elif any(k in manufacturer for k in ['sony computer entertainment', 'nintendo']):
        return 'Gaming'
    elif any(k in text for k in ['playstation', 'xbox', 'nintendo', 'steam deck']):
        return 'Gaming'
    
    # Smart TV and streaming devices
    elif any(k in manufacturer for k in ['roku', 'nvidia', 'chromecast']):
        return 'Streaming'
    elif any(k in text for k in ['roku', 'chromecast', 'nvidia shield', 'apple tv']):
        return 'Streaming'
    
    else:
        return 'Other'

def parse_frequency(interface_info):
    """Parse frequency information"""
    try:
        if interface_info is None:
            return 'N/A', 'Unknown'
        
        freq = interface_info.get('frequency')
        if freq is None or freq == 'N/A' or freq == '':
            return 'N/A', 'Unknown'
        
        freq_value = float(freq)
        if 2.4 <= freq_value < 2.5:
            band = '2.4GHz'
        elif 5.0 <= freq_value < 6.0:
            band = '5GHz'
        elif 6.0 <= freq_value < 7.0:
            band = '6GHz'
        else:
            band = 'Unknown'
        
        return f"{freq} GHz", band
    except:
        return 'N/A', 'Unknown'

def convert_signal_dbm_to_percent(signal_dbm):
    """Convert dBm to percentage"""
    try:
        if not signal_dbm or signal_dbm == 'N/A':
            return 0
        dbm = float(str(signal_dbm).replace(' dBm', '').strip())
        if dbm >= -50:
            return 100
        elif dbm <= -100:
            return 0
        else:
            return int(2 * (dbm + 100))
    except:
        return 0

def get_signal_quality(signal_dbm):
    """Get signal quality description"""
    try:
        if not signal_dbm or signal_dbm == 'N/A':
            return 'Unknown'
        dbm = float(str(signal_dbm).replace(' dBm', '').strip())
        if dbm >= -50:
            return 'Excellent'
        elif dbm >= -60:
            return 'Very Good'
        elif dbm >= -70:
            return 'Good'
        elif dbm >= -80:
            return 'Fair'
        else:
            return 'Poor'
    except:
        return 'Unknown'

def update_cache():
    """Update data cache with latest device information"""
    global data_cache
    try:
        logging.info("Starting cache update...")
        all_devices = eero_api.get_all_devices()
        
        # Validate we got actual device data
        if not all_devices:
            logging.warning("No devices returned from API - keeping previous cache")
            # Still update the timestamp so we know we tried
            if 'last_update' in data_cache:
                data_cache['last_update'] = datetime.now().isoformat()
            return
        
        # Include both wired and wireless connected devices
        connected_devices = [d for d in all_devices if d.get('connected')]
        
        # If we get 0 connected devices but had devices before, it might be a temporary API issue
        previous_device_count = len(data_cache.get('devices', []))
        if len(connected_devices) == 0 and previous_device_count > 0:
            logging.warning(f"API returned 0 devices but we had {previous_device_count} before - keeping previous cache")
            return
        
        wireless_devices = [d for d in connected_devices if d.get('wireless')]
        
        logging.info(f"Processing {len(connected_devices)} connected devices ({len(wireless_devices)} wireless)")
        
        # Process devices for detailed view
        device_list = []
        os_counts = {'iOS': 0, 'Android': 0, 'Windows': 0, 'Amazon': 0, 'Gaming': 0, 'Streaming': 0, 'Other': 0}
        freq_counts = {'2.4GHz': 0, '5GHz': 0, '6GHz': 0}
        signal_values = []
        
        # Process all connected devices for OS detection
        for device in connected_devices:
            # OS Detection (for all devices)
            device_os = detect_device_os(device)
            os_counts[device_os] += 1
            
            # Frequency and Signal only for wireless devices
            is_wireless = device.get('wireless', False)
            interface_info = device.get('interface', {}) if is_wireless else {}
            
            if is_wireless:
                freq_display, freq_band = parse_frequency(interface_info)
                if freq_band in freq_counts:
                    freq_counts[freq_band] += 1
                
                # Signal Strength (wireless only)
                signal_dbm = interface_info.get('signal_dbm', 'N/A')
                signal_percent = convert_signal_dbm_to_percent(signal_dbm)
                signal_quality = get_signal_quality(signal_dbm)
                
                if signal_dbm != 'N/A':
                    try:
                        signal_values.append(float(str(signal_dbm).replace(' dBm', '').strip()))
                    except:
                        pass
            else:
                # Wired device
                freq_display = 'Wired'
                freq_band = 'Wired'
                signal_dbm = 'N/A'
                signal_percent = 100  # Wired connections are always "full strength"
                signal_quality = 'Wired'
            
            device_list.append({
                'name': device.get('nickname') or device.get('hostname') or 'Unknown Device',
                'ip': ', '.join(device.get('ips', [])) if device.get('ips') else 'N/A',
                'mac': device.get('mac', 'N/A'),
                'manufacturer': device.get('manufacturer', 'Unknown'),
                'device_os': device_os,
                'connection_type': 'Wireless' if is_wireless else 'Wired',
                'frequency': freq_display,
                'frequency_band': freq_band,
                'signal_avg_dbm': f"{signal_dbm} dBm" if signal_dbm != 'N/A' else 'N/A',
                'signal_avg': signal_percent,
                'signal_quality': signal_quality
            })
        
        # Update connected users history (keep last 168 points for 1 week of hourly data)
        # Now counts all connected devices (wired + wireless)
        current_time = datetime.now()
        connected_users = data_cache.get('connected_users', [])
        connected_users.append({
            'timestamp': current_time.isoformat(),
            'count': len(connected_devices)
        })
        if len(connected_users) > 168:  # Keep 1 week of hourly data
            connected_users = connected_users[-168:]
        
        # Update signal strength history (keep last 168 points for 1 week of hourly data)
        # Signal strength only applies to wireless devices
        signal_strength_avg = data_cache.get('signal_strength_avg', [])
        if signal_values:
            avg_signal = sum(signal_values) / len(signal_values)
            signal_strength_avg.append({
                'timestamp': current_time.isoformat(),
                'avg_dbm': round(avg_signal, 1)
            })
        if len(signal_strength_avg) > 168:  # Keep 1 week of hourly data
            signal_strength_avg = signal_strength_avg[-168:]
        
        # Update cache
        data_cache.update({
            'connected_users': connected_users,
            'device_os': os_counts,
            'frequency_distribution': freq_counts,
            'signal_strength_avg': signal_strength_avg,
            'devices': device_list,
            'total_devices': len(connected_devices),
            'wireless_devices': len(wireless_devices),
            'wired_devices': len(connected_devices) - len(wireless_devices),
            'last_update': current_time.isoformat(),
            'last_successful_update': current_time.isoformat()
        })
        
        # Save historical data to persistent storage
        save_history(data_cache)
        
        logging.info(f"Cache updated successfully: {len(connected_devices)} total devices ({len(wireless_devices)} wireless, {len(connected_devices) - len(wireless_devices)} wired)")
        
    except Exception as e:
        logging.error(f"Cache update error: {e}")
        # Update last_update timestamp even on error, but keep last_successful_update unchanged
        if 'last_update' in data_cache:
            data_cache['last_update'] = datetime.now().isoformat()

def filter_data_by_timerange(data, hours):
    """Filter time-series data by hours"""
    if not data or hours == 0:
        return data
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    return [
        entry for entry in data 
        if datetime.fromisoformat(entry['timestamp']) >= cutoff_time
    ]

# Routes - Exact replica of macOS version
@app.route('/')
def index():
    """Serve main dashboard page"""
    try:
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r') as f:
                return f.read()
    except Exception as e:
        logging.error(f"Template load error: {e}")
    
    # Fallback minimal HTML
    return '''<!DOCTYPE html>
<html><head><title>MiniRack Dashboard</title></head>
<body><h1>Dashboard Loading...</h1>
<p>Please wait while the dashboard initializes.</p>
<script>setTimeout(() => location.reload(), 5000);</script>
</body></html>'''

# API Routes (same as full version)
@app.route('/api/dashboard')
def get_dashboard_data():
    update_cache()
    return jsonify(data_cache)

@app.route('/api/dashboard/<int:hours>')
def get_dashboard_data_filtered(hours):
    """Get dashboard data filtered by time range"""
    update_cache()
    filtered_cache = data_cache.copy()
    
    # Filter time-series data
    filtered_cache['connected_users'] = filter_data_by_timerange(data_cache['connected_users'], hours)
    filtered_cache['signal_strength_avg'] = filter_data_by_timerange(data_cache['signal_strength_avg'], hours)
    
    return jsonify(filtered_cache)

@app.route('/api/network')
def get_network_info():
    """Get network information"""
    try:
        network_info = eero_api.get_network_info()
        return jsonify({
            'name': network_info.get('name', 'Unknown Network'),
            'network_id': eero_api.network_id,
            'success': True
        })
    except Exception as e:
        return jsonify({
            'name': 'Unknown Network',
            'network_id': eero_api.network_id,
            'success': False,
            'error': str(e)
        })

@app.route('/api/devices')
def get_devices():
    return jsonify({
        'devices': data_cache.get('devices', []),
        'count': len(data_cache.get('devices', []))
    })

@app.route('/api/version')
def get_version():
    config = load_config()
    return jsonify({
        'version': VERSION,
        'network_id': config.get('network_id'),
        'environment': config.get('environment', 'production'),
        'api_url': config.get('api_url', 'api-user.e2ro.com'),
        'authenticated': eero_api.api_token is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/admin/update', methods=['POST'])
def update_dashboard():
    """Update dashboard from GitHub - completely self-contained"""
    try:
        logging.info("Starting dashboard update from GitHub...")
        
        # Download files directly using requests - no external dependencies
        files_to_update = [
            {
                'url': 'https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/dashboard_minimal.py',
                'path': '/opt/eero/app/dashboard.py'
            },
            {
                'url': 'https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/index.html', 
                'path': '/opt/eero/app/index.html'
            }
        ]
        
        # Download and save each file
        for file_info in files_to_update:
            logging.info(f"Downloading {file_info['url']}")
            
            response = requests.get(file_info['url'], timeout=30)
            response.raise_for_status()
            
            # Create backup
            backup_path = f"{file_info['path']}.backup"
            if os.path.exists(file_info['path']):
                with open(file_info['path'], 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            # Write new file
            with open(file_info['path'], 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Set file permissions (owner: www-data, group: www-data, mode: 644)
            os.chown(file_info['path'], 33, 33)  # www-data uid/gid
            os.chmod(file_info['path'], 0o644)
            
            logging.info(f"Updated {file_info['path']}")
        
        # Set directory permissions
        os.chown('/opt/eero/app', 33, 33)
        os.chmod('/opt/eero/app', 0o755)
        
        # Restart service using absolute path with proper sudo handling
        logging.info("Restarting eero-dashboard service...")
        
        # Try different approaches for restarting the service
        restart_commands = [
            ['/usr/bin/sudo', '/usr/bin/systemctl', 'restart', 'eero-dashboard'],
            ['/bin/sudo', '/bin/systemctl', 'restart', 'eero-dashboard'],
            ['/usr/bin/systemctl', 'restart', 'eero-dashboard'],
            ['/bin/systemctl', 'restart', 'eero-dashboard']
        ]
        
        restart_success = False
        for cmd in restart_commands:
            try:
                restart_result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'}
                )
                
                if restart_result.returncode == 0:
                    restart_success = True
                    logging.info(f"Service restarted successfully using: {' '.join(cmd)}")
                    break
                else:
                    logging.warning(f"Command {' '.join(cmd)} failed: {restart_result.stderr}")
            except Exception as e:
                logging.warning(f"Command {' '.join(cmd)} exception: {str(e)}")
                continue
        
        if not restart_success:
            logging.error("All restart attempts failed")
            return jsonify({
                'success': False, 
                'message': 'Files updated but service restart failed. Please restart manually with: sudo systemctl restart eero-dashboard'
            }), 500
        
        logging.info("Dashboard update completed successfully")
        return jsonify({
            'success': True, 
            'message': 'Dashboard code updated successfully! Reloading in 3 seconds...'
        })
        
    except requests.RequestException as e:
        logging.error(f"Download error: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Download failed: {str(e)}'
        }), 500
    except OSError as e:
        logging.error(f"File operation error: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'File operation failed: {str(e)}'
        }), 500
    except Exception as e:
        logging.error(f"Update error: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Update error: {str(e)}'
        }), 500

@app.route('/api/admin/network-id', methods=['POST'])
def change_network_id():
    try:
        data = request.get_json()
        new_id = data.get('network_id', '').strip()
        
        if not new_id or not new_id.isdigit():
            return jsonify({'success': False, 'message': 'Invalid network ID'}), 400
        
        config = load_config()
        config['network_id'] = new_id
        
        if save_config(config):
            eero_api.network_id = new_id
            return jsonify({'success': True, 'message': f'Network ID updated to {new_id}'})
        
        return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/reauthorize', methods=['POST'])
def reauthorize():
    try:
        data = request.get_json()
        step = data.get('step', 'send')
        
        if step == 'send':
            email = data.get('email', '').strip()
            if not email or '@' not in email:
                return jsonify({'success': False, 'message': 'Invalid email'}), 400
            
            logging.info(f"Sending verification code to {email}")
            response = requests.post(
                f"https://{eero_api.api_url}/2.2/pro/login",
                json={"login": email},
                timeout=10
            )
            response.raise_for_status()
            response_data = response.json()
            
            logging.info(f"Login response: {response_data}")
            
            if 'data' not in response_data or 'user_token' not in response_data['data']:
                return jsonify({'success': False, 'message': 'Failed to generate token'}), 500
            
            with open(TOKEN_FILE + '.temp', 'w') as f:
                f.write(response_data['data']['user_token'])
            os.chmod(TOKEN_FILE + '.temp', 0o600)
            
            return jsonify({'success': True, 'message': 'Verification code sent to email'})
            
        elif step == 'verify':
            code = data.get('code', '').strip()
            if not code:
                return jsonify({'success': False, 'message': 'Code required'}), 400
            
            temp_file = TOKEN_FILE + '.temp'
            if not os.path.exists(temp_file):
                return jsonify({'success': False, 'message': 'Please restart authentication process'}), 400
            
            with open(temp_file, 'r') as f:
                token = f.read().strip()
            
            logging.info(f"Verifying code: {code}")
            
            # Try both form data and JSON for verification
            verify_methods = [
                # Method 1: Form data (original eero API format)
                lambda: requests.post(
                    f"https://{eero_api.api_url}/2.2/login/verify",
                    headers={"X-User-Token": token, "Content-Type": "application/x-www-form-urlencoded"},
                    data={"code": code},
                    timeout=10
                ),
                # Method 2: JSON data
                lambda: requests.post(
                    f"https://{eero_api.api_url}/2.2/login/verify",
                    headers={"X-User-Token": token, "Content-Type": "application/json"},
                    json={"code": code},
                    timeout=10
                )
            ]
            
            verify_response = None
            for i, method in enumerate(verify_methods):
                try:
                    verify_response = method()
                    verify_response.raise_for_status()
                    verify_data = verify_response.json()
                    logging.info(f"Verify method {i+1} response: {verify_data}")
                    
                    # Check for successful verification
                    if (verify_data.get('data', {}).get('email', {}).get('verified') or 
                        verify_data.get('data', {}).get('verified') or
                        verify_response.status_code == 200):
                        
                        # Save the token
                        with open(TOKEN_FILE, 'w') as f:
                            f.write(token)
                        os.chmod(TOKEN_FILE, 0o600)
                        
                        # Clean up temp file
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        
                        # Update API token
                        eero_api.api_token = token
                        logging.info("Authentication successful")
                        
                        return jsonify({'success': True, 'message': 'Authentication successful!'})
                    
                except requests.RequestException as e:
                    logging.warning(f"Verify method {i+1} failed: {str(e)}")
                    continue
                except Exception as e:
                    logging.warning(f"Verify method {i+1} exception: {str(e)}")
                    continue
            
            # If we get here, all methods failed
            if verify_response:
                logging.error(f"Verification failed. Last response: {verify_response.text}")
                return jsonify({'success': False, 'message': f'Verification failed. Please check the code and try again.'}), 400
            else:
                return jsonify({'success': False, 'message': 'Network error during verification. Please try again.'}), 500
            
    except requests.RequestException as e:
        logging.error(f"Network error during reauthorization: {str(e)}")
        return jsonify({'success': False, 'message': f'Network error: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Reauthorization error: {str(e)}")
        return jsonify({'success': False, 'message': f'Authentication error: {str(e)}'}), 500

def periodic_save():
    """Periodically save historical data"""
    while True:
        try:
            time.sleep(300)  # Save every 5 minutes
            if data_cache.get('connected_users'):
                save_history(data_cache)
if __name__ == '__main__':
    logging.info(f"Starting MiniRack Dashboard {VERSION}")
    
    # Initial cache update
    try:
        update_cache()
        logging.info("Initial cache update complete")
    except Exception as e:
        logging.warning(f"Initial cache update failed: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)