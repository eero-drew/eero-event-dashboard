#!/bin/bash
# Complete Dashboard Installation and Fix Script
# Handles fresh installs and fixes broken installations

set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

echo "🚀 MiniRack Dashboard - Complete Installation/Fix Script"
echo "======================================================"

# Check if this is a fresh install or a fix
if [ ! -d "/opt/eero" ]; then
    echo "📦 Fresh installation detected"
    FRESH_INSTALL=true
else
    echo "🔧 Existing installation detected - will fix/update"
    FRESH_INSTALL=false
fi

# Stop any existing services
echo "⏹️ Stopping existing services..."
sudo systemctl stop eero-dashboard 2>/dev/null || echo "   Dashboard service not running"
sudo systemctl stop nginx 2>/dev/null || echo "   Nginx not running"

# Install system packages if needed
if $FRESH_INSTALL; then
    echo "📦 Installing system packages..."
    sudo apt-get update -y
    sudo apt-get install -y python3-pip nginx curl python3-venv
fi

# Create directories
echo "📁 Creating directories..."
sudo mkdir -p /opt/eero/{app,logs,backups}

# Download application files
echo "📥 Downloading MiniRack Dashboard v6.7.1..."
sudo curl -o /opt/eero/app/dashboard.py https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/dashboard_minimal.py
sudo curl -o /opt/eero/app/index.html https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/index.html
sudo curl -o /opt/eero/app/config.json https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/config.json
sudo curl -o /opt/eero/app/requirements.txt https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/requirements.txt

# Verify downloads
if [ ! -f "/opt/eero/app/dashboard.py" ] || [ ! -f "/opt/eero/app/index.html" ]; then
    echo "❌ Download failed - files missing"
    exit 1
fi

echo "✅ Files downloaded successfully"

# Setup Python environment
echo "🐍 Setting up Python environment..."
cd /opt/eero

# Remove existing venv if it has permission issues
if [ -d "venv" ]; then
    echo "   Removing existing venv with potential permission issues..."
    sudo rm -rf venv
fi

# Create fresh virtual environment
echo "   Creating fresh virtual environment..."
sudo -u www-data python3 -m venv venv

# Install packages
echo "   Installing Python packages..."
sudo -u www-data /opt/eero/venv/bin/pip install --upgrade pip
sudo -u www-data /opt/eero/venv/bin/pip install -r app/requirements.txt

# Set permissions
echo "🔐 Setting permissions..."
sudo chown -R www-data:www-data /opt/eero
sudo chmod +x /opt/eero/app/dashboard.py
sudo chmod 644 /opt/eero/app/index.html
sudo chmod 644 /opt/eero/app/config.json

# Create/recreate systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/eero-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=MiniRack Dashboard
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/eero/app
Environment=PATH=/opt/eero/venv/bin
ExecStart=/opt/eero/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 dashboard:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

# Test Python syntax
echo "🔍 Testing Python syntax..."
sudo -u www-data /opt/eero/venv/bin/python -c "import sys; sys.path.insert(0, '/opt/eero/app'); import dashboard; print('✅ Python syntax OK')"

# Configure Nginx - AGGRESSIVELY prevent default page
echo "🌐 Configuring nginx (anti-default-page mode)..."
sudo systemctl stop nginx 2>/dev/null || true

# Remove ALL nginx default content
sudo rm -rf /var/www/html/* /var/www/* /etc/nginx/sites-enabled/* /etc/nginx/sites-available/default* /etc/nginx/conf.d/* 2>/dev/null || true

# Create clean nginx configuration
sudo tee /etc/nginx/nginx.conf > /dev/null << 'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;

    # ONLY serve dashboard - no defaults anywhere
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        
        # Disable any default root or index
        root /nonexistent;
        
        # Proxy EVERYTHING to our dashboard
        location / {
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
            proxy_buffering off;
        }
        
        # Catch any other attempts to serve files
        location ~* \.(html|htm)$ {
            proxy_pass http://127.0.0.1:5000;
        }
    }
}
EOF

# Test nginx configuration
echo "✅ Testing nginx configuration..."
sudo nginx -t

# Reload systemd and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable eero-dashboard
sudo systemctl start eero-dashboard

# Wait for dashboard to be ready
echo "⏳ Waiting for dashboard service to start..."
for i in {1..30}; do
    if sudo systemctl is-active --quiet eero-dashboard; then
        echo "✅ Dashboard service is active"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Dashboard service failed to start"
        sudo systemctl status eero-dashboard
        sudo journalctl -u eero-dashboard --no-pager -n 20
        exit 1
    fi
    sleep 2
done

# Test dashboard directly
echo "🔍 Testing dashboard on port 5000..."
for i in {1..20}; do
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Dashboard responding on port 5000"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Dashboard not responding on port 5000"
        sudo systemctl status eero-dashboard
        sudo journalctl -u eero-dashboard --no-pager -n 20
        exit 1
    fi
    echo "⏳ Attempt $i: Waiting for dashboard..."
    sleep 2
done

# Start nginx
echo "🌐 Starting nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx

# Wait for nginx
sleep 3

# Test complete setup with anti-default-page verification
echo "🔍 Testing complete setup (anti-default-page verification)..."
for i in {1..10}; do
    RESPONSE=$(curl -s http://localhost/)
    
    if echo "$RESPONSE" | grep -q "Dashboard" && ! echo "$RESPONSE" | grep -q "Welcome to nginx"; then
        echo "✅ Test $i: Dashboard serving correctly"
        DASHBOARD_WORKING=true
        break
    else
        echo "⚠️ Test $i: Incorrect content detected"
        if [ $i -eq 10 ]; then
            echo "❌ All tests failed - still getting wrong content"
            echo "Response preview (first 300 chars):"
            echo "$RESPONSE" | head -c 300
            echo ""
            echo "Debugging information:"
            sudo systemctl status nginx eero-dashboard
            echo "Nginx error log:"
            sudo tail -10 /var/log/nginx/error.log 2>/dev/null || echo "No nginx error log"
            exit 1
        fi
    fi
    sleep 2
done

# Configure firewall if needed
if command -v ufw >/dev/null 2>&1; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 80/tcp >/dev/null 2>&1 || true
    sudo ufw allow 22/tcp >/dev/null 2>&1 || true
    sudo ufw --force enable >/dev/null 2>&1 || true
fi

# Success message
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "your-lightsail-ip")
echo ""
echo "🎉 MiniRack Dashboard installation/fix completed successfully!"
echo "======================================================"
echo "🌐 Dashboard URL: http://$PUBLIC_IP"
echo "📋 Version: 6.7.1-persistent"
echo ""
echo "🆕 FEATURES AVAILABLE:"
echo "   • Multi-network monitoring (up to 6 networks)"
echo "   • Individual API authentication per network"
echo "   • Timezone configuration"
echo "   • Data persistence across restarts"
echo "   • Chart reliability improvements"
echo "   • π Admin panel with full management"
echo ""
echo "🔧 NEXT STEPS:"
echo "   1. Access the dashboard at the URL above"
echo "   2. Click the π button (bottom-right corner)"
echo "   3. Go to 'Manage Networks' to add your networks"
echo "   4. Configure timezone and authenticate networks"
echo ""
echo "✅ Services Status:"
echo "   • Dashboard Service: $(sudo systemctl is-active eero-dashboard)"
echo "   • Nginx Service: $(sudo systemctl is-active nginx)"
echo "   • Dashboard Health: $(curl -s http://localhost:5000/health | grep -o '"status":"[^"]*"' || echo 'Not responding')"