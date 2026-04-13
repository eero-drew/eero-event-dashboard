# MiniRack Dashboard - macOS Local Setup

Run the complete MiniRack Dashboard locally on your Mac with full mobile responsive design and multi-network support.

## 🚀 Quick Start

### Option 1: Simple Local Version (Recommended)
```bash
# Run the simple local dashboard (no external dependencies)
python3 dashboard_simple_local.py
```

### Option 2: Full Local Version
```bash
# Run the setup script
python3 setup_macos_local.py

# Start the dashboard
./run_local.sh
```

### Option 3: Manual Setup
```bash
# Install dependencies
pip3 install flask==2.3.3 flask-cors==4.0.0 requests==2.31.0 pytz==2023.3

# Run the dashboard
python3 dashboard_local.py
```

## 📱 Access Your Dashboard

- **URL**: http://localhost:3000
- **Admin Panel**: Click the π button
- **Mobile Responsive**: Works on all devices
- **Multi-Network**: Support for up to 6 networks

## ⚙️ Configuration

### Local Configuration Directory
- **Location**: `~/.minirack/`
- **Config File**: `~/.minirack/config.json`
- **Logs**: `~/.minirack/dashboard.log`
- **Cache**: `~/.minirack/data_cache.json`

### Network Setup
1. Open http://localhost:3000
2. Click the π button (bottom right)
3. Click "Manage Networks"
4. Add your network ID and email
5. Authenticate with the real verification code sent to your email

## 🔧 Features

### ✅ Complete Feature Set
- **Mobile Responsive Design** - Perfect on all screen sizes
- **Multi-Network Support** - Monitor up to 6 networks
- **Real-time Device Monitoring** - Wired and wireless devices
- **Full-Height Network Display** - Per-network info fills entire column
- **Eero Insight Integration** - Clickable network ID links
- **CSV Data Export** - Complete network and device statistics
- **Frequency Distribution** - 2.4GHz, 5GHz, 6GHz breakdown
- **Device Type Detection** - iOS, Android, Windows, Amazon, etc.
- **Time Range Selection** - 1h, 4h, 8h, 12h, 24h, week
- **Per-Network Statistics** - Individual network breakdowns
- **Production API Integration** - Real Eero API authentication and data

### 📊 Dashboard Charts
1. **Connected Devices** - Timeline of device connections
2. **Device Types** - Pie chart of device OS distribution
3. **Frequency Distribution** - Wireless frequency usage
4. **Per-Network Information** - Full-height static display with:
   - Network authentication status
   - Device counts (total, wireless, wired)
   - Device type breakdown by network
   - Frequency distribution by network
   - Clickable Eero Insight links
   - Last update timestamps

### 📥 Data Export
- **CSV Export Button** - Located in header next to time range selector
- **Comprehensive Data** - All networks, device counts, frequencies
- **Timestamped Files** - Automatic filename with export timestamp
- **Eero Insight Links** - Direct links to network management

### 🔐 Network Authentication
- **Real Eero API Authentication** - Production email verification
- Secure token storage in `~/.minirack/`
- Multiple network support with individual authentication
- Individual network enable/disable

## 🛠️ Troubleshooting

### "Failed to load networks" Error - FIXED ✅
This issue has been resolved! The local dashboard now includes all necessary network management API endpoints.

### Dependencies Issues
```bash
# If you get import errors
pip3 install --upgrade flask flask-cors requests pytz

# For Python version issues
python3 --version  # Should be 3.8+
```

### Port Conflicts
If port 3000 is in use:
```bash
# Kill existing processes
lsof -ti:3000 | xargs kill -9

# Or edit dashboard_simple_local.py and change the port:
app.run(host='127.0.0.1', port=3001, debug=True)  # Use port 3001
```

### Configuration Issues
```bash
# Reset configuration
rm -rf ~/.minirack/
python3 dashboard_simple_local.py  # Will recreate defaults
```

### Network Authentication
- **Real Eero API**: Email-based verification with production API
- Check spam folder for verification codes
- Codes expire after a few minutes
- Try the authentication process again if needed

## 📁 File Structure

```
minirackdash/
├── dashboard_simple_local.py   # ⭐ Simple local version (recommended)
├── dashboard_local.py          # Full local macOS runner
├── run_local.sh               # Convenience script
├── setup_macos_local.py       # Automatic setup
├── deploy/
│   ├── dashboard_minimal.py   # Main dashboard code
│   ├── index.html            # Frontend (mobile responsive)
│   └── requirements.txt      # Dependencies
└── ~/.minirack/              # Local config directory
    ├── config.json           # Network configuration
    ├── dashboard.log         # Application logs
    ├── data_cache.json       # Cached data
    └── .eero_token*          # Authentication tokens
```

## 🔄 Updates

To update to the latest version:
```bash
git pull origin eeroNetworkDash
python3 dashboard_simple_local.py  # Restart with new code
```

## 🌐 Deployment vs Local

| Feature | Local macOS | AWS Lightsail |
|---------|-------------|---------------|
| **URL** | localhost:3000 | Public IP |
| **Config** | ~/.minirack/ | /opt/eero/ |
| **Service** | Manual start | systemd |
| **Logs** | ~/.minirack/dashboard.log | /opt/eero/logs/ |
| **Updates** | git pull | Deployment scripts |
| **Authentication** | Production API | Production API only |

## 📞 Support

- **Version**: 6.8.0-mobile-local
- **Features**: All production features included
- **Mobile**: Fully responsive design
- **Networks**: Multi-network support with CSV export
- **Debug**: Console logging and debug endpoints
- **Fixed**: Network management API endpoints working with real production authentication
- **New**: Full-height per-network display with Eero Insight links and CSV export

Your local dashboard has the same features as the production AWS version!