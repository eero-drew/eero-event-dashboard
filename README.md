# Eero Event Dashboard v6.8.0

A comprehensive, mobile-responsive dashboard for monitoring multiple Eero networks with real-time device tracking, analytics, and data export capabilities.

![Dashboard Preview](https://img.shields.io/badge/Version-6.8.0-blue) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20AWS-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Features

### 📊 Real-Time Network Monitoring
- **Multi-Network Support**: Monitor up to 6 Eero networks simultaneously
- **Live Device Tracking**: Real-time connected device counts (wired + wireless)
- **Device Type Detection**: Automatic categorization (iOS, Android, Windows, Amazon, Gaming, Streaming)
- **Frequency Analysis**: 2.4GHz, 5GHz, and 6GHz distribution per network
- **Authentication Status**: Visual indicators for network connection status

### 📱 Mobile-First Design
- **Responsive Layout**: 1 column (mobile) → 2 columns (tablet) → 4 columns (desktop)
- **Touch-Optimized**: Perfect for phones, tablets, and desktop
- **Fluid Typography**: Scales beautifully across all screen sizes
- **Chart Stability**: No sliding animations or layout shifts

### 🔗 Eero Integration
- **Production API**: Real Eero API authentication with email verification
- **Insight Links**: Clickable network IDs link directly to Eero Insight dashboard
- **Network Management**: Add, remove, and manage multiple networks
- **Secure Authentication**: Individual token storage per network

### 📈 Data Export & Analytics
- **CSV Export**: One-click export of all network and device data
- **Comprehensive Data**: Device counts, types, frequencies, and timestamps
- **Timestamped Files**: Automatic filename generation with export time
- **Direct Links**: CSV includes Eero Insight URLs for each network

### ⏱️ Time Range Analysis
- **Flexible Timeframes**: 1h, 4h, 8h, 12h, 24h, and 1 week views
- **Historical Data**: Up to 168 data points (1 week of hourly data)
- **Real-Time Updates**: Automatic refresh every few minutes

## 🖥️ Dashboard Layout

### Main Charts (3-column responsive grid)
1. **Connected Devices Timeline**: Historical device connection data
2. **Device Types Distribution**: Pie chart of device OS breakdown
3. **Frequency Distribution**: Wireless frequency usage across networks

### Per-Network Information Panel (Full-height 4th column)
- **Network Authentication Status**: Green ✓ Connected / Red ✗ Not Connected
- **Device Counts**: Total, wireless, and wired devices per network
- **Device Type Breakdown**: Color-coded badges with counts
- **Frequency Distribution**: 2.4GHz, 5GHz, 6GHz usage per network
- **Clickable Network IDs**: Direct links to Eero Insight
- **Last Update Timestamps**: Real-time sync status

## 🚀 Quick Start

### Local macOS Development
```bash
# Clone the repository
git clone https://github.com/Drew-CodeRGV/eero-event-dashboard.git
cd eero-event-dashboard

# Run the simple local version (recommended)
python3 dashboard_simple_local.py

# Access at http://localhost:3000
```

### AWS Lightsail Deployment
```bash
# One-command deployment
curl -s https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main/lightsail_launch_script.sh | bash
```

## 📋 Requirements

### Local Development
- **Python 3.8+**
- **Dependencies**: `flask flask-cors requests pytz`
- **macOS**: Tested on macOS (should work on Linux/Windows)

### AWS Deployment
- **Lightsail Instance**: $5/month plan minimum
- **Ubuntu 20.04+**: Automatic setup via launch script
- **Static IP**: Recommended for consistent access

## 🔧 Configuration

### Network Setup
1. **Access Dashboard**: Open http://localhost:3000 (local) or your Lightsail IP
2. **Admin Panel**: Click the π button (bottom right)
3. **Manage Networks**: Click "Manage Networks"
4. **Add Network**: Enter Network ID and email address
5. **Authenticate**: Enter verification code sent to your email
6. **Monitor**: Dashboard will start showing real-time data

### Configuration Files
- **Local**: `~/.minirack/config.json`
- **AWS**: `/opt/eero/app/config.json`
- **Tokens**: Stored securely per network
- **Logs**: Available for debugging and monitoring

## 📊 API Endpoints

### Data Endpoints
- `GET /api/dashboard` - Main dashboard data
- `GET /api/dashboard/<hours>` - Time-filtered data
- `GET /api/networks` - Network configuration
- `GET /api/network-stats` - Per-network statistics
- `GET /api/devices` - Device list
- `GET /api/version` - Version and status info

### Export Endpoints
- `GET /api/export/csv` - Download CSV export

### Admin Endpoints
- `POST /api/admin/networks` - Add network
- `DELETE /api/admin/networks/<id>` - Remove network
- `POST /api/admin/networks/<id>/toggle` - Enable/disable network
- `POST /api/admin/networks/<id>/auth` - Authenticate network
- `POST /api/admin/timezone` - Change timezone

## 📁 File Structure

```
eero-event-dashboard/
├── README.md                    # This file
├── dashboard_simple_local.py    # ⭐ Recommended local version
├── dashboard_local.py           # Full local version
├── setup_macos_local.py         # Automatic local setup
├── run_local.sh                # Convenience script
├── README_macOS_Local.md        # Detailed local setup guide
├── lightsail_launch_script.sh   # AWS deployment script
├── complete_dashboard_install.sh # Manual AWS setup
└── deploy/
    ├── dashboard_minimal.py     # Production version
    ├── index.html              # Mobile-responsive frontend
    ├── requirements.txt        # Python dependencies
    └── config.json             # Default configuration
```

## 🔐 Security Features

- **Email Verification**: Production Eero API authentication
- **Secure Token Storage**: Individual encrypted tokens per network
- **Permission Management**: Enable/disable networks independently
- **Local Configuration**: Sensitive data stored locally only
- **HTTPS Ready**: SSL/TLS support for production deployments

## 📱 Mobile Experience

### Responsive Breakpoints
- **Mobile (< 768px)**: Single column layout, touch-optimized
- **Tablet (768px - 1024px)**: Two-column grid
- **Desktop (> 1024px)**: Full four-column layout

### Touch Optimizations
- **Large Touch Targets**: Minimum 44px touch areas
- **Swipe-Friendly**: Smooth scrolling and navigation
- **Readable Typography**: Fluid font sizing with clamp()
- **Fast Loading**: Optimized for mobile networks

## 📈 CSV Export Format

The CSV export includes comprehensive data:

| Column | Description |
|--------|-------------|
| Network Name | User-defined network name |
| Network ID | Eero network identifier |
| API Name | Network name from Eero API |
| Authenticated | Connection status (Yes/No) |
| Total Devices | All connected devices |
| Wireless/Wired | Connection type breakdown |
| Device Types | iOS, Android, Windows, Amazon, Gaming, Streaming, Other |
| Frequencies | 2.4GHz, 5GHz, 6GHz device counts |
| Last Update | Timestamp of last data sync |
| Insight Link | Direct URL to Eero Insight |

## 🚀 Deployment Options

### 1. Local Development (Recommended for testing)
- **Pros**: Easy setup, real-time development, secure local access
- **Cons**: Only accessible from your machine
- **Best for**: Development, testing, personal use

### 2. AWS Lightsail (Recommended for production)
- **Pros**: Public access, reliable hosting, automatic backups
- **Cons**: Monthly cost ($5+), requires AWS account
- **Best for**: Team access, remote monitoring, production use

### 3. Self-Hosted Server
- **Pros**: Full control, no monthly fees
- **Cons**: Requires server management, security updates
- **Best for**: Advanced users, existing infrastructure

## 🔄 Version History

- **v6.8.0**: Full-height per-network display, Eero Insight links, CSV export
- **v6.7.9**: Real production authentication for local development
- **v6.7.8**: Mobile responsive design and chart stability fixes
- **v6.7.7**: Multi-network support and enhanced device detection
- **v6.7.6**: Timezone support and data persistence

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check README_macOS_Local.md for detailed setup
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions

## 🙏 Acknowledgments

- **Eero API**: For providing network access capabilities
- **Chart.js**: For beautiful, responsive charts
- **Font Awesome**: For clean, professional icons
- **Flask**: For the lightweight Python web framework

---

**Made with ❤️ for Eero network monitoring**

*Transform your network monitoring experience with real-time insights, beautiful visualizations, and comprehensive data export capabilities.*