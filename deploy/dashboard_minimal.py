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
import pytz

# Configuration
VERSION = "6.8.0-mobile"
CONFIG_FILE = "/opt/eero/app/config.json"
TOKEN_FILE = "/opt/eero/app/.eero_token"
TEMPLATE_FILE = "/opt/eero/app/index.html"
DATA_CACHE_FILE = "/opt/eero/app/data_cache.json"

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
                    # Keep old fields for backward compatibility
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
        "environment": "production",
        "api_url": "api-user.e2ro.com",
        "timezone": "UTC"
    }

def save_config(config):
    """Save configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        logging.error("Config save error: " + str(e))
        return False

def get_timezone_aware_now():
    """Get current time in configured timezone"""
    try:
        config = load_config()
        tz_name = config.get('timezone', 'UTC')
        tz = pytz.timezone(tz_name)
        return datetime.now(tz)
    except Exception as e:
        logging.warning("Timezone error, using UTC: " + str(e))
        return datetime.now(pytz.UTC)

def save_data_cache():
    """Save data cache to disk for persistence"""
    try:
        # Create a serializable copy of the cache
        cache_copy = {}
        for key, value in data_cache.items():
            if key == 'networks':
                # Save network data
                cache_copy[key] = {}
                for net_id, net_data in value.items():
                    cache_copy[key][net_id] = net_data.copy()
            else:
                cache_copy[key] = value.copy() if isinstance(value, dict) else value
        
        # Add timestamp for cache validation
        cache_copy['_saved_at'] = get_timezone_aware_now().isoformat()
        
        with open(DATA_CACHE_FILE, 'w') as f:
            json.dump(cache_copy, f, indent=2)
        
        # Set proper permissions
        os.chmod(DATA_CACHE_FILE, 0o644)
        logging.info("Data cache saved to disk")
        return True
    except Exception as e:
        logging.error("Failed to save data cache: " + str(e))
        return False

def load_data_cache():
    """Load data cache from disk"""
    try:
        if os.path.exists(DATA_CACHE_FILE):
            with open(DATA_CACHE_FILE, 'r') as f:
                saved_cache = json.load(f)
            
            # Check if cache is not too old (max 24 hours)
            saved_at = saved_cache.get('_saved_at')
            if saved_at:
                saved_time = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                current_time = get_timezone_aware_now()
                
                # Convert to UTC for comparison if needed
                if saved_time.tzinfo is None:
                    saved_time = pytz.UTC.localize(saved_time)
                if current_time.tzinfo != saved_time.tzinfo:
                    current_time = current_time.astimezone(pytz.UTC)
                    saved_time = saved_time.astimezone(pytz.UTC)
                
                age_hours = (current_time - saved_time).total_seconds() / 3600
                
                if age_hours > 24:
                    logging.info(f"Cached data is {age_hours:.1f} hours old, starting fresh")
                    return None
            
            # Remove metadata
            if '_saved_at' in saved_cache:
                del saved_cache['_saved_at']
            
            logging.info("Loaded data cache from disk")
            return saved_cache
    except Exception as e:
        logging.error("Failed to load data cache: " + str(e))
    
    return None

class EeroAPI:
    def __init__(self):
        self.session = requests.Session()
        self.config = load_config()
        self.api_url = self.config.get('api_url', 'api-user.e2ro.com')
        self.api_base = "https://" + self.api_url + "/2.2"
        
        # Load tokens for all networks
        self.network_tokens = {}
        self.load_all_tokens()
    
    def load_all_tokens(self):
        """Load API tokens for all configured networks"""
        try:
            networks = self.config.get('networks', [])
            for network in networks:
                network_id = network.get('id')
                if network_id:
                    token_file = f"/opt/eero/app/.eero_token_{network_id}"
                    if os.path.exists(token_file):
                        with open(token_file, 'r') as f:
                            self.network_tokens[network_id] = f.read().strip()
                    else:
                        # Check if token is stored in network config
                        token = network.get('token', '')
                        if token:
                            self.network_tokens[network_id] = token
        except Exception as e:
            logging.error("Token loading error: " + str(e))
    
    def get_headers(self, network_id):
        """Get request headers for specific network"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MiniRack-Dashboard/' + VERSION
        }
        token = self.network_tokens.get(network_id)
        if token:
            headers['X-User-Token'] = token
        return headers
    
    def get_network_info(self, network_id):
        """Get network information including name"""
        try:
            url = self.api_base + "/networks/" + network_id
            response = self.session.get(url, headers=self.get_headers(network_id), timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                network_data = data['data']
                logging.info(f"Retrieved network info for {network_id}: {network_data.get('name', 'Unknown')}")
                return network_data
            return {}
        except Exception as e:
            logging.error(f"Network info fetch error for {network_id}: {str(e)}")
            return {}
    
    def get_all_devices(self, network_id):
        """Get all devices for specific network with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = self.api_base + "/networks/" + network_id + "/devices"
                response = self.session.get(url, headers=self.get_headers(network_id), timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if 'data' in data:
                    devices = data['data'] if isinstance(data['data'], list) else data['data'].get('devices', [])
                    logging.info(f"Retrieved {len(devices)} devices from network {network_id} (attempt {attempt + 1})")
                    return devices
                
                logging.warning(f"No data in response for network {network_id} (attempt {attempt + 1}): {str(data)}")
                return []
                
            except requests.exceptions.Timeout:
                logging.warning(f"API timeout for network {network_id} on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.RequestException as e:
                logging.warning(f"API request error for network {network_id} on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except Exception as e:
                logging.error(f"Device fetch error for network {network_id} on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
        
        logging.error(f"All device fetch attempts failed for network {network_id}")
        return []

# Initialize API
eero_api = EeroAPI()

# Data cache - now supports multiple networks with persistence
def initialize_data_cache():
    """Initialize data cache, loading from disk if available"""
    default_cache = {
        'networks': {},  # Will store data per network ID
        'combined': {     # Combined data from all active networks
            'connected_users': [],
            'device_os': {},
            'frequency_distribution': {},
            'signal_strength_avg': [],
            'devices': [],
            'last_update': None
        }
    }
    
    # Try to load existing cache
    saved_cache = load_data_cache()
    if saved_cache:
        # Merge saved cache with default structure
        for key in default_cache:
            if key in saved_cache:
                default_cache[key] = saved_cache[key]
        logging.info("Restored data cache from disk")
    
    return default_cache

data_cache = initialize_data_cache()

def detect_device_os(device):
    """Detect device OS from manufacturer and hostname"""
    manufacturer = str(device.get('manufacturer', '')).lower()
    hostname = str(device.get('hostname', '')).lower()
    text = manufacturer + " " + hostname
    
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
        
        return str(freq) + " GHz", band
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
    """Update data cache with latest device information from all networks"""
    global data_cache
    try:
        logging.info("Starting multi-network cache update...")
        config = load_config()
        networks = config.get('networks', [])
        active_networks = [n for n in networks if n.get('active', True)]
        
        if not active_networks:
            logging.warning("No active networks configured")
            return
        
        # Initialize combined data
        combined_devices = []
        combined_os_counts = {'iOS': 0, 'Android': 0, 'Windows': 0, 'Amazon': 0, 'Gaming': 0, 'Streaming': 0, 'Other': 0}
        combined_freq_counts = {'2.4GHz': 0, '5GHz': 0, '6GHz': 0}
        combined_signal_values = []
        current_time = get_timezone_aware_now()
        
        # Process each active network
        for network in active_networks:
            network_id = network.get('id')
            if not network_id:
                continue
                
            logging.info(f"Processing network {network_id} ({network.get('name', 'Unknown')})")
            
            # Get devices for this network
            network_devices = eero_api.get_all_devices(network_id)
            
            if not network_devices:
                logging.warning(f"No devices returned for network {network_id}")
                continue
            
            # Filter connected devices
            connected_devices = [d for d in network_devices if d.get('connected')]
            wireless_devices = [d for d in connected_devices if d.get('wireless')]
            
            logging.info(f"Network {network_id}: {len(connected_devices)} connected devices ({len(wireless_devices)} wireless)")
            
            # Initialize network cache if not exists
            if network_id not in data_cache['networks']:
                data_cache['networks'][network_id] = {
                    'connected_users': [],
                    'signal_strength_avg': [],
                    'devices': [],
                    'last_update': None,
                    'last_successful_update': None
                }
            
            network_cache = data_cache['networks'][network_id]
            
            # Process devices for this network
            network_device_list = []
            network_os_counts = {'iOS': 0, 'Android': 0, 'Windows': 0, 'Amazon': 0, 'Gaming': 0, 'Streaming': 0, 'Other': 0}
            network_freq_counts = {'2.4GHz': 0, '5GHz': 0, '6GHz': 0}
            network_signal_values = []
            
            for device in connected_devices:
                # OS Detection
                device_os = detect_device_os(device)
                network_os_counts[device_os] += 1
                combined_os_counts[device_os] += 1
                
                # Connection type and frequency
                is_wireless = device.get('wireless', False)
                interface_info = device.get('interface', {}) if is_wireless else {}
                
                if is_wireless:
                    freq_display, freq_band = parse_frequency(interface_info)
                    if freq_band in network_freq_counts:
                        network_freq_counts[freq_band] += 1
                        combined_freq_counts[freq_band] += 1
                    
                    # Signal Strength - Enhanced debugging and collection
                    signal_dbm = interface_info.get('signal_dbm', 'N/A')
                    logging.debug(f"Device {device.get('nickname', 'Unknown')}: signal_dbm = {signal_dbm}, interface_info = {interface_info}")
                    
                    signal_percent = convert_signal_dbm_to_percent(signal_dbm)
                    signal_quality = get_signal_quality(signal_dbm)
                    
                    if signal_dbm != 'N/A' and signal_dbm is not None:
                        try:
                            # Handle different signal_dbm formats
                            if isinstance(signal_dbm, (int, float)):
                                signal_val = float(signal_dbm)
                            else:
                                signal_val = float(str(signal_dbm).replace(' dBm', '').replace('dBm', '').strip())
                            
                            # Only add valid signal values (typical range -100 to -30 dBm)
                            if -100 <= signal_val <= -10:
                                network_signal_values.append(signal_val)
                                combined_signal_values.append(signal_val)
                                logging.debug(f"Added signal value: {signal_val} dBm")
                            else:
                                logging.warning(f"Signal value out of range: {signal_val} dBm")
                        except (ValueError, TypeError) as e:
                            logging.warning(f"Could not parse signal_dbm '{signal_dbm}': {e}")
                            pass
                else:
                    freq_display = 'Wired'
                    freq_band = 'Wired'
                    signal_dbm = 'N/A'
                    signal_percent = 100
                    signal_quality = 'Wired'
                
                device_info = {
                    'name': device.get('nickname') or device.get('hostname') or 'Unknown Device',
                    'ip': ', '.join(device.get('ips', [])) if device.get('ips') else 'N/A',
                    'mac': device.get('mac', 'N/A'),
                    'manufacturer': device.get('manufacturer', 'Unknown'),
                    'device_os': device_os,
                    'connection_type': 'Wireless' if is_wireless else 'Wired',
                    'frequency': freq_display,
                    'frequency_band': freq_band,
                    'signal_avg_dbm': str(signal_dbm) + " dBm" if signal_dbm != 'N/A' else 'N/A',
                    'signal_avg': signal_percent,
                    'signal_quality': signal_quality,
                    'network_id': network_id,
                    'network_name': network.get('name', f'Network {network_id}')
                }
                
                network_device_list.append(device_info)
                combined_devices.append(device_info)
            
            # Update network-specific history
            network_connected_users = network_cache.get('connected_users', [])
            network_connected_users.append({
                'timestamp': current_time.isoformat(),
                'count': len(connected_devices)
            })
            if len(network_connected_users) > 168:
                network_connected_users = network_connected_users[-168:]
            
            network_signal_strength_avg = network_cache.get('signal_strength_avg', [])
            if network_signal_values:
                avg_signal = sum(network_signal_values) / len(network_signal_values)
                logging.info(f"Network {network_id}: {len(network_signal_values)} wireless devices, avg signal: {avg_signal:.1f} dBm")
                network_signal_strength_avg.append({
                    'timestamp': current_time.isoformat(),
                    'avg_dbm': round(avg_signal, 1)
                })
            else:
                logging.info(f"Network {network_id}: No wireless devices with valid signal data")
            if len(network_signal_strength_avg) > 168:
                network_signal_strength_avg = network_signal_strength_avg[-168:]
            
            # Update network cache
            network_cache.update({
                'connected_users': network_connected_users,
                'signal_strength_avg': network_signal_strength_avg,
                'devices': network_device_list,
                'device_os': network_os_counts,
                'frequency_distribution': network_freq_counts,
                'total_devices': len(connected_devices),
                'wireless_devices': len(wireless_devices),
                'wired_devices': len(connected_devices) - len(wireless_devices),
                'last_update': current_time.isoformat(),
                'last_successful_update': current_time.isoformat()
            })
        
        # Update combined cache
        combined_connected_users = data_cache['combined'].get('connected_users', [])
        total_combined_devices = len(combined_devices)
        combined_connected_users.append({
            'timestamp': current_time.isoformat(),
            'count': total_combined_devices
        })
        if len(combined_connected_users) > 168:
            combined_connected_users = combined_connected_users[-168:]
        
        combined_signal_strength_avg = data_cache['combined'].get('signal_strength_avg', [])
        if combined_signal_values:
            avg_signal = sum(combined_signal_values) / len(combined_signal_values)
            logging.info(f"Combined: {len(combined_signal_values)} total wireless devices, avg signal: {avg_signal:.1f} dBm")
            combined_signal_strength_avg.append({
                'timestamp': current_time.isoformat(),
                'avg_dbm': round(avg_signal, 1)
            })
        else:
            logging.info("Combined: No wireless devices with valid signal data across all networks")
        if len(combined_signal_strength_avg) > 168:
            combined_signal_strength_avg = combined_signal_strength_avg[-168:]
        
        # Calculate combined wireless/wired counts
        combined_wireless = len([d for d in combined_devices if d['connection_type'] == 'Wireless'])
        combined_wired = len(combined_devices) - combined_wireless
        
        data_cache['combined'].update({
            'connected_users': combined_connected_users,
            'device_os': combined_os_counts,
            'frequency_distribution': combined_freq_counts,
            'signal_strength_avg': combined_signal_strength_avg,
            'devices': combined_devices,
            'total_devices': total_combined_devices,
            'wireless_devices': combined_wireless,
            'wired_devices': combined_wired,
            'last_update': current_time.isoformat(),
            'last_successful_update': current_time.isoformat(),
            'active_networks': len(active_networks)
        })
        
        logging.info(f"Multi-network cache updated: {len(active_networks)} networks, {total_combined_devices} total devices")
        
        # Save cache to disk for persistence
        save_data_cache()
        
    except Exception as e:
        logging.error("Multi-network cache update error: " + str(e))
        # Update last_update timestamp even on error
        current_time = get_timezone_aware_now()
        data_cache['combined']['last_update'] = current_time.isoformat()
        # Still try to save cache even on error to preserve existing data
        save_data_cache()

def filter_data_by_timerange(data, hours):
    """Filter time-series data by hours"""
    if not data or hours == 0:
        return data
    
    cutoff_time = get_timezone_aware_now() - timedelta(hours=hours)
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
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # Verify we have the full dashboard content
                if 'showAdmin' in content and 'π' in content and len(content) > 10000:
                    logging.info("Serving full dashboard template (" + str(len(content)) + " chars)")
                    return content
                else:
                    logging.warning("Template file exists but appears incomplete")
        else:
            logging.error("Template file not found: " + TEMPLATE_FILE)
    except Exception as e:
        logging.error("Template load error: " + str(e))
    
    # Fallback minimal HTML
    return '''<!DOCTYPE html>
<html><head><title>MiniRack Dashboard</title></head>
<body><h1>Dashboard Loading...</h1>
<p>Please wait while the dashboard initializes.</p>
<script>setTimeout(() => location.reload(), 5000);</script>
</body></html>'''

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': VERSION})

# API Routes (same as full version)
@app.route('/api/dashboard')
def get_dashboard_data():
    update_cache()
    return jsonify(data_cache['combined'])

@app.route('/api/dashboard/<int:hours>')
def get_dashboard_data_filtered(hours):
    """Get dashboard data filtered by time range"""
    update_cache()
    filtered_cache = data_cache['combined'].copy()
    
    # Filter time-series data
    filtered_cache['connected_users'] = filter_data_by_timerange(data_cache['combined']['connected_users'], hours)
    filtered_cache['signal_strength_avg'] = filter_data_by_timerange(data_cache['combined']['signal_strength_avg'], hours)
    
    return jsonify(filtered_cache)

@app.route('/api/networks')
def get_networks():
    """Get all configured networks"""
    config = load_config()
    networks = config.get('networks', [])
    
    # Add authentication status for each network
    for network in networks:
        network_id = network.get('id')
        network['authenticated'] = network_id in eero_api.network_tokens
        
        # Get network name from API if available
        if network['authenticated']:
            try:
                network_info = eero_api.get_network_info(network_id)
                if network_info.get('name'):
                    network['api_name'] = network_info['name']
            except:
                pass
    
    return jsonify({'networks': networks})

@app.route('/api/network')
def get_network_info():
    """Get primary network information (backward compatibility)"""
    try:
        config = load_config()
        networks = config.get('networks', [])
        
        if networks:
            primary_network = networks[0]
            network_id = primary_network.get('id')
            
            if network_id in eero_api.network_tokens:
                network_info = eero_api.get_network_info(network_id)
                return jsonify({
                    'name': network_info.get('name', primary_network.get('name', 'Unknown Network')),
                    'network_id': network_id,
                    'success': True
                })
        
        return jsonify({
            'name': 'Multi-Network Dashboard',
            'network_id': 'multiple',
            'success': True
        })
    except Exception as e:
        return jsonify({
            'name': 'Multi-Network Dashboard',
            'network_id': 'multiple',
            'success': False,
            'error': str(e)
        })

@app.route('/api/network-stats')
def get_network_stats():
    """Get detailed statistics for each network"""
    try:
        config = load_config()
        networks = config.get('networks', [])
        active_networks = [n for n in networks if n.get('active', True)]
        
        network_stats = []
        
        for network in active_networks:
            network_id = network.get('id')
            if not network_id or network_id not in data_cache.get('networks', {}):
                continue
                
            network_cache = data_cache['networks'][network_id]
            
            # Get network info
            network_info = {
                'id': network_id,
                'name': network.get('name', f'Network {network_id}'),
                'authenticated': network_id in eero_api.network_tokens,
                'total_devices': network_cache.get('total_devices', 0),
                'wireless_devices': network_cache.get('wireless_devices', 0),
                'wired_devices': network_cache.get('wired_devices', 0),
                'device_os': network_cache.get('device_os', {}),
                'frequency_distribution': network_cache.get('frequency_distribution', {}),
                'last_update': network_cache.get('last_update'),
                'last_successful_update': network_cache.get('last_successful_update')
            }
            
            # Add API network name if available
            if network_info['authenticated']:
                try:
                    api_network_info = eero_api.get_network_info(network_id)
                    if api_network_info.get('name'):
                        network_info['api_name'] = api_network_info['name']
                except:
                    pass
            
            network_stats.append(network_info)
        
        return jsonify({
            'networks': network_stats,
            'total_networks': len(network_stats),
            'combined_stats': data_cache.get('combined', {})
        })
        
    except Exception as e:
        logging.error(f"Network stats error: {str(e)}")
        return jsonify({'networks': [], 'total_networks': 0, 'combined_stats': {}}), 500

@app.route('/api/debug/signal')
def debug_signal():
    """Debug endpoint for signal strength data"""
    try:
        debug_info = {
            'combined_signal_data': data_cache['combined'].get('signal_strength_avg', []),
            'combined_signal_count': len(data_cache['combined'].get('signal_strength_avg', [])),
            'networks': {}
        }
        
        # Add per-network signal data
        for network_id, network_data in data_cache.get('networks', {}).items():
            debug_info['networks'][network_id] = {
                'signal_data': network_data.get('signal_strength_avg', []),
                'signal_count': len(network_data.get('signal_strength_avg', [])),
                'wireless_devices': network_data.get('wireless_devices', 0),
                'last_update': network_data.get('last_update')
            }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices')
def get_devices():
    return jsonify({
        'devices': data_cache['combined'].get('devices', []),
        'count': len(data_cache['combined'].get('devices', []))
    })

@app.route('/api/version')
def get_version():
    config = load_config()
    current_time = get_timezone_aware_now()
    networks = config.get('networks', [])
    
    # For backward compatibility, use first network ID if available
    primary_network_id = networks[0].get('id') if networks else 'multiple'
    
    return jsonify({
        'version': VERSION,
        'network_id': primary_network_id,
        'networks_count': len(networks),
        'environment': config.get('environment', 'production'),
        'api_url': config.get('api_url', 'api-user.e2ro.com'),
        'timezone': config.get('timezone', 'UTC'),
        'authenticated': len(eero_api.network_tokens) > 0,
        'timestamp': current_time.isoformat(),
        'local_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    })

@app.route('/api/admin/backup-data', methods=['POST'])
def backup_data():
    """Backup current data cache before operations"""
    try:
        if save_data_cache():
            # Also create a timestamped backup
            backup_file = f"/opt/eero/app/data_cache_backup_{int(time.time())}.json"
            import shutil
            shutil.copy2(DATA_CACHE_FILE, backup_file)
            os.chmod(backup_file, 0o644)
            
            return jsonify({'success': True, 'message': 'Data backed up successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to backup data'}), 500
    except Exception as e:
        logging.error(f"Backup error: {str(e)}")
        return jsonify({'success': False, 'message': f'Backup error: {str(e)}'}), 500

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
            logging.info("Downloading " + file_info['url'])
            
            response = requests.get(file_info['url'], timeout=30)
            response.raise_for_status()
            
            # Create backup
            backup_path = file_info['path'] + ".backup"
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
            
            logging.info("Updated " + file_info['path'])
        
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
                    logging.info("Service restarted successfully using: " + ' '.join(cmd))
                    break
                else:
                    logging.warning("Command " + ' '.join(cmd) + " failed: " + restart_result.stderr)
            except Exception as e:
                logging.warning("Command " + ' '.join(cmd) + " exception: " + str(e))
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
        logging.error("Download error: " + str(e))
        return jsonify({
            'success': False, 
            'message': 'Download failed: ' + str(e)
        }), 500
    except OSError as e:
        logging.error("File operation error: " + str(e))
        return jsonify({
            'success': False, 
            'message': 'File operation failed: ' + str(e)
        }), 500
    except Exception as e:
        logging.error("Update error: " + str(e))
        return jsonify({
            'success': False, 
            'message': 'Update error: ' + str(e)
        }), 500

@app.route('/api/admin/networks', methods=['POST'])
def add_network():
    """Add a new network to monitor"""
    try:
        data = request.get_json()
        network_id = data.get('network_id', '').strip()
        email = data.get('email', '').strip()
        name = data.get('name', '').strip() or f'Network {network_id}'
        
        if not network_id or not network_id.isdigit():
            return jsonify({'success': False, 'message': 'Invalid network ID'}), 400
        
        if not email or '@' not in email:
            return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
        config = load_config()
        networks = config.get('networks', [])
        
        # Check if network already exists
        if any(n.get('id') == network_id for n in networks):
            return jsonify({'success': False, 'message': 'Network already exists'}), 400
        
        # Check network limit (max 6)
        if len(networks) >= 6:
            return jsonify({'success': False, 'message': 'Maximum 6 networks allowed'}), 400
        
        # Add new network
        new_network = {
            'id': network_id,
            'name': name,
            'email': email,
            'token': '',
            'active': True
        }
        
        networks.append(new_network)
        config['networks'] = networks
        
        if save_config(config):
            return jsonify({
                'success': True, 
                'message': f'Network {name} added. Please authenticate to start monitoring.',
                'network': new_network
            })
        
        return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/networks/<network_id>', methods=['DELETE'])
def remove_network(network_id):
    """Remove a network from monitoring"""
    try:
        config = load_config()
        networks = config.get('networks', [])
        
        # Find and remove network
        networks = [n for n in networks if n.get('id') != network_id]
        
        if len(networks) == len(config.get('networks', [])):
            return jsonify({'success': False, 'message': 'Network not found'}), 404
        
        config['networks'] = networks
        
        if save_config(config):
            # Remove token file if exists
            token_file = f"/opt/eero/app/.eero_token_{network_id}"
            if os.path.exists(token_file):
                os.remove(token_file)
            
            # Remove from memory
            if network_id in eero_api.network_tokens:
                del eero_api.network_tokens[network_id]
            
            return jsonify({'success': True, 'message': f'Network {network_id} removed'})
        
        return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/networks/<network_id>/toggle', methods=['POST'])
def toggle_network(network_id):
    """Toggle network active status"""
    try:
        config = load_config()
        networks = config.get('networks', [])
        
        # Find and toggle network
        for network in networks:
            if network.get('id') == network_id:
                network['active'] = not network.get('active', True)
                config['networks'] = networks
                
                if save_config(config):
                    status = 'enabled' if network['active'] else 'disabled'
                    return jsonify({'success': True, 'message': f'Network {network_id} {status}'})
                
                return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500
        
        return jsonify({'success': False, 'message': 'Network not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/networks/<network_id>/auth', methods=['POST'])
def authenticate_network(network_id):
    """Authenticate a specific network"""
    try:
        data = request.get_json()
        step = data.get('step', 'send')
        
        # Find network
        config = load_config()
        networks = config.get('networks', [])
        network = next((n for n in networks if n.get('id') == network_id), None)
        
        if not network:
            return jsonify({'success': False, 'message': 'Network not found'}), 404
        
        if step == 'send':
            # Allow email to be provided in request, fallback to stored email
            email = data.get('email', '').strip()
            if not email:
                email = network.get('email', '')
            
            if not email:
                return jsonify({'success': False, 'message': 'Email address required for authentication'}), 400
            
            if '@' not in email:
                return jsonify({'success': False, 'message': 'Invalid email address'}), 400
            
            logging.info(f"Sending verification code to {email} for network {network_id}")
            response = requests.post(
                f"https://{eero_api.api_url}/2.2/pro/login",
                json={"login": email},
                timeout=10
            )
            response.raise_for_status()
            response_data = response.json()
            
            if 'data' not in response_data or 'user_token' not in response_data['data']:
                return jsonify({'success': False, 'message': 'Failed to generate token'}), 500
            
            # Store temporary token
            temp_token_file = f"/opt/eero/app/.eero_token_{network_id}.temp"
            with open(temp_token_file, 'w') as f:
                f.write(response_data['data']['user_token'])
            os.chmod(temp_token_file, 0o600)
            
            return jsonify({'success': True, 'message': f'Verification code sent to {email}'})
            
        elif step == 'verify':
            code = data.get('code', '').strip()
            if not code:
                return jsonify({'success': False, 'message': 'Code required'}), 400
            
            temp_token_file = f"/opt/eero/app/.eero_token_{network_id}.temp"
            if not os.path.exists(temp_token_file):
                return jsonify({'success': False, 'message': 'Please restart authentication process'}), 400
            
            with open(temp_token_file, 'r') as f:
                token = f.read().strip()
            
            # Verify code
            verify_response = requests.post(
                f"https://{eero_api.api_url}/2.2/login/verify",
                headers={"X-User-Token": token, "Content-Type": "application/x-www-form-urlencoded"},
                data={"code": code},
                timeout=10
            )
            verify_response.raise_for_status()
            verify_data = verify_response.json()
            
            if (verify_data.get('data', {}).get('email', {}).get('verified') or 
                verify_data.get('data', {}).get('verified') or
                verify_response.status_code == 200):
                
                # Save permanent token
                token_file = f"/opt/eero/app/.eero_token_{network_id}"
                with open(token_file, 'w') as f:
                    f.write(token)
                os.chmod(token_file, 0o600)
                
                # Clean up temp file
                if os.path.exists(temp_token_file):
                    os.remove(temp_token_file)
                
                # Update in-memory tokens
                eero_api.network_tokens[network_id] = token
                
                logging.info(f"Authentication successful for network {network_id}")
                return jsonify({'success': True, 'message': f'Network {network_id} authenticated successfully!'})
            else:
                return jsonify({'success': False, 'message': 'Verification failed. Please check the code.'}), 400
            
    except requests.RequestException as e:
        logging.error(f"Network authentication error for {network_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Network error: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Network authentication error for {network_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Authentication error: {str(e)}'}), 500

@app.route('/api/admin/timezone', methods=['POST'])
def change_timezone():
    try:
        data = request.get_json()
        new_timezone = data.get('timezone', '').strip()
        
        # Validate timezone
        try:
            pytz.timezone(new_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            return jsonify({'success': False, 'message': 'Invalid timezone'}), 400
        
        config = load_config()
        config['timezone'] = new_timezone
        
        if save_config(config):
            return jsonify({'success': True, 'message': 'Timezone updated to ' + new_timezone})
        
        return jsonify({'success': False, 'message': 'Failed to save configuration'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
            return jsonify({'success': True, 'message': 'Network ID updated to ' + new_id})
        
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
            
            logging.info("Sending verification code to " + email)
            response = requests.post(
                "https://" + eero_api.api_url + "/2.2/pro/login",
                json={"login": email},
                timeout=10
            )
            response.raise_for_status()
            response_data = response.json()
            
            logging.info("Login response: " + str(response_data))
            
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
            
            logging.info("Verifying code: " + code)
            
            # Try both form data and JSON for verification
            verify_methods = [
                # Method 1: Form data (original eero API format)
                lambda: requests.post(
                    "https://" + eero_api.api_url + "/2.2/login/verify",
                    headers={"X-User-Token": token, "Content-Type": "application/x-www-form-urlencoded"},
                    data={"code": code},
                    timeout=10
                ),
                # Method 2: JSON data
                lambda: requests.post(
                    "https://" + eero_api.api_url + "/2.2/login/verify",
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
                    logging.info("Verify method " + str(i+1) + " response: " + str(verify_data))
                    
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
                    logging.warning("Verify method " + str(i+1) + " failed: " + str(e))
                    continue
                except Exception as e:
                    logging.warning("Verify method " + str(i+1) + " exception: " + str(e))
                    continue
            
            # If we get here, all methods failed
            if verify_response:
                logging.error("Verification failed. Last response: " + verify_response.text)
                return jsonify({'success': False, 'message': 'Verification failed. Please check the code and try again.'}), 400
            else:
                return jsonify({'success': False, 'message': 'Network error during verification. Please try again.'}), 500
            
    except requests.RequestException as e:
        logging.error("Network error during reauthorization: " + str(e))
        return jsonify({'success': False, 'message': 'Network error: ' + str(e)}), 500
    except Exception as e:
        logging.error("Reauthorization error: " + str(e))
        return jsonify({'success': False, 'message': 'Authentication error: ' + str(e)}), 500

@app.route('/api/export/csv')
def export_csv():
    """Export network data to CSV"""
    try:
        import csv
        from io import StringIO
        
        # Get current network stats
        config = load_config()
        networks = config.get('networks', [])
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Network Name', 'Network ID', 'API Name', 'Authenticated', 
            'Total Devices', 'Wireless Devices', 'Wired Devices',
            'iOS Devices', 'Android Devices', 'Windows Devices', 'Amazon Devices',
            'Gaming Devices', 'Streaming Devices', 'Other Devices',
            '2.4GHz Devices', '5GHz Devices', '6GHz Devices',
            'Last Update', 'Insight Link'
        ])
        
        # Write network data
        for network in networks:
            network_id = network.get('id')
            network_cache = data_cache.get('networks', {}).get(network_id, {})
            device_os = network_cache.get('device_os', {})
            freq_dist = network_cache.get('frequency_distribution', {})
            
            # Get API name if authenticated
            api_name = ''
            if network_id in eero_api.network_tokens:
                try:
                    network_info = eero_api.get_network_info(network_id)
                    api_name = network_info.get('name', '')
                except:
                    pass
            
            writer.writerow([
                network.get('name', f'Network {network_id}'),
                network_id,
                api_name,
                'Yes' if network_id in eero_api.network_tokens else 'No',
                network_cache.get('total_devices', 0),
                network_cache.get('wireless_devices', 0),
                network_cache.get('wired_devices', 0),
                device_os.get('iOS', 0),
                device_os.get('Android', 0),
                device_os.get('Windows', 0),
                device_os.get('Amazon', 0),
                device_os.get('Gaming', 0),
                device_os.get('Streaming', 0),
                device_os.get('Other', 0),
                freq_dist.get('2.4GHz', 0),
                freq_dist.get('5GHz', 0),
                freq_dist.get('6GHz', 0),
                network_cache.get('last_successful_update', ''),
                f'https://insight.eero.com/networks/{network_id}'
            ])
        
        # Prepare response
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'eero_network_export_{timestamp}.csv'
        
        # Return CSV file
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        logging.error(f"CSV export error: {str(e)}")
        return jsonify({'error': 'Failed to generate CSV export'}), 500

if __name__ == '__main__':
    logging.info("Starting MiniRack Dashboard " + VERSION)
    
    # Initial cache update
    try:
        update_cache()
        logging.info("Initial cache update complete")
    except Exception as e:
        logging.warning("Initial cache update failed: " + str(e))
    
    app.run(host='0.0.0.0', port=5000, debug=False)