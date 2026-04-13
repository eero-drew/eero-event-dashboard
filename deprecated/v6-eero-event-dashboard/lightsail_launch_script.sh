#!/bin/bash
# MiniRack Dashboard - Lightsail Launch Script (Under 16KB)
# Downloads and installs the full v6.7.1 dashboard from GitHub

set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Update and install essentials
apt-get update -y
apt-get install -y python3-pip nginx curl python3-venv

# Create directories
mkdir -p /opt/eero/{app,logs}

# Download application files from GitHub
echo "📥 Downloading MiniRack Dashboard v6.7.1..."
curl -o /opt/eero/app/dashboard.py https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/dashboard_minimal.py
curl -o /opt/eero/app/index.html https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/index.html
curl -o /opt/eero/app/config.json https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/config.json
curl -o /opt/eero/app/requirements.txt https://raw.githubusercontent.com/Drew-CodeRGV/minirackdash/eeroNetworkDash/deploy/requirements.txt

# Verify downloads
if [ ! -f "/opt/eero/app/dashboard.py" ] || [ ! -f "/opt/eero/app/index.html" ]; then
    echo "❌ Download failed"
    exit 1
fi

echo "✅ Files downloaded successfully"

# Setup Python environment
cd /opt/eero

# Remove any existing venv with potential permission issues
if [ -d "venv" ]; then
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt

# Set permissions AFTER creating venv
chown -R www-data:www-data /opt/eero
chmod +x /opt/eero/app/dashboard.py

# Create systemd service
cat > /etc/systemd/system/eero-dashboard.service << 'EOF'
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
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx - AGGRESSIVELY prevent default page
echo "🌐 Configuring nginx to ONLY serve dashboard..."
sudo systemctl stop nginx || true
sudo rm -rf /var/www/html/* /var/www/* /etc/nginx/sites-enabled/* /etc/nginx/sites-available/default* /etc/nginx/conf.d/*
cat > /etc/nginx/nginx.conf << 'EOF'
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

    # ONLY serve dashboard - no defaults
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        root /nonexistent;
        
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
    }
}
EOF

# Start services with verification
systemctl daemon-reload
systemctl enable eero-dashboard
systemctl start eero-dashboard

# Wait for Flask app
echo "⏳ Starting dashboard service..."
for i in {1..20}; do
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Dashboard service ready"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Dashboard service failed to start"
        systemctl status eero-dashboard
        exit 1
    fi
    sleep 2
done

# Start nginx
systemctl enable nginx
systemctl restart nginx

# Verify complete setup with multiple checks
echo "🔍 Testing nginx proxy with multiple verification checks..."
for i in {1..10}; do
    RESPONSE=$(curl -s http://localhost/)
    if echo "$RESPONSE" | grep -q "Dashboard" && ! echo "$RESPONSE" | grep -q "Welcome to nginx"; then
        echo "✅ Nginx proxy working correctly (test $i)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Nginx still serving default page after 10 attempts"
        echo "Response preview: $(echo "$RESPONSE" | head -c 200)"
        systemctl status nginx
        exit 1
    fi
    echo "⏳ Test $i: Waiting for proper proxy setup..."
    sleep 2
done

# Configure firewall
ufw allow 80/tcp
ufw allow 22/tcp
ufw --force enable

# Success message
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "your-lightsail-ip")
echo ""
echo "🎉 MiniRack Dashboard v6.7.1 installed successfully!"
echo "🌐 Access your dashboard: http://$PUBLIC_IP"
echo ""
echo "🆕 FEATURES INCLUDED:"
echo "   • Multi-network monitoring (up to 6 networks)"
echo "   • Individual API authentication per network"
echo "   • Timezone configuration"
echo "   • Data persistence across restarts"
echo "   • Chart reliability improvements"
echo "   • π Admin panel with full management"
echo ""
echo "🔧 NEXT STEPS:"
echo "   1. Click the π button (bottom-right corner)"
echo "   2. Go to 'Manage Networks' to add your networks"
echo "   3. Configure timezone in admin panel"
echo "   4. Authenticate each network individually"
echo ""
echo "📋 Version: 6.7.1-persistent with multi-network support"