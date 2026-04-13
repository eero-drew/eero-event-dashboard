#!/bin/bash
# =============================================================================
# MiniRack Dashboard - Raspberry Pi 5 Installer
# For a fresh Raspberry Pi 5 running Raspberry Pi OS (Bookworm)
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main/deploy/pi_installer.sh | bash
#   -- or --
#   chmod +x deploy/pi_installer.sh && sudo ./deploy/pi_installer.sh
# =============================================================================

set -e

# --- Configuration ---
APP_DIR="/opt/eero"
APP_USER="eero"
REPO_URL="https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main"
DASHBOARD_PORT=5000
NGINX_PORT=80

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}"; }

# --- Root check ---
if [ "$EUID" -ne 0 ]; then
    err "Please run as root: sudo $0"
    exit 1
fi

# --- Detect Pi ---
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null && [ ! -f /sys/firmware/devicetree/base/model ]; then
    warn "This doesn't look like a Raspberry Pi. Continuing anyway..."
fi

PI_MODEL=$(cat /sys/firmware/devicetree/base/model 2>/dev/null || echo "Unknown")
log "🍓 Detected: $PI_MODEL"
log "🚀 Starting MiniRack Dashboard installation..."

# --- Step 1: System update & dependencies ---
log "📦 Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

log "📦 Installing dependencies..."
apt-get install -y -qq \
    python3 \
    python3-venv \
    python3-pip \
    nginx \
    curl \
    git \
    sqlite3

# --- Step 2: Create service user ---
if ! id "$APP_USER" &>/dev/null; then
    log "👤 Creating service user: $APP_USER"
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
else
    log "👤 Service user $APP_USER already exists"
fi

# --- Step 3: Create directory structure ---
log "📁 Setting up application directories..."
mkdir -p "$APP_DIR"/{app,logs,backups}

# --- Step 4: Download application files ---
log "⬇️  Downloading application files..."
curl -sfL "$REPO_URL/deploy/dashboard_minimal.py" -o "$APP_DIR/app/dashboard.py"
curl -sfL "$REPO_URL/deploy/index.html"            -o "$APP_DIR/app/index.html"
curl -sfL "$REPO_URL/deploy/config.json"            -o "$APP_DIR/app/config.json"
curl -sfL "$REPO_URL/deploy/requirements.txt"       -o "$APP_DIR/app/requirements.txt"

# Verify download
if [ ! -f "$APP_DIR/app/dashboard.py" ]; then
    err "Failed to download dashboard.py"
    exit 1
fi
log "✅ Application files downloaded"

# --- Step 5: Python virtual environment ---
log "🐍 Creating Python virtual environment..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

log "📦 Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "$APP_DIR/app/requirements.txt" -q

deactivate
log "✅ Python environment ready"

# --- Step 6: Set permissions ---
log "🔐 Setting file permissions..."
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
chmod 700 "$APP_DIR/app/config.json"

# --- Step 7: Create systemd service ---
log "⚙️  Creating systemd service..."
cat > /etc/systemd/system/eero-dashboard.service << EOF
[Unit]
Description=MiniRack Eero Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/app
Environment=PATH=$APP_DIR/venv/bin:/usr/bin:/bin
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    --bind 127.0.0.1:$DASHBOARD_PORT \\
    --workers 2 \\
    --timeout 120 \\
    --access-logfile $APP_DIR/logs/access.log \\
    --error-logfile $APP_DIR/logs/error.log \\
    dashboard:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# --- Step 8: Configure nginx ---
log "🌐 Configuring nginx..."
cat > /etc/nginx/sites-available/eero-dashboard << EOF
server {
    listen $NGINX_PORT default_server;
    listen [::]:$NGINX_PORT default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$DASHBOARD_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 60s;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/eero-dashboard /etc/nginx/sites-enabled/

nginx -t 2>/dev/null
log "✅ Nginx configured"

# --- Step 9: Create update script ---
log "🔄 Creating update helper..."
cat > "$APP_DIR/update.sh" << 'UPDATEEOF'
#!/bin/bash
set -e
echo "🔄 Updating MiniRack Dashboard..."
REPO="https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main"
curl -sfL "$REPO/deploy/dashboard_minimal.py" -o /opt/eero/app/dashboard.py
curl -sfL "$REPO/deploy/index.html"            -o /opt/eero/app/index.html
chown eero:eero /opt/eero/app/dashboard.py /opt/eero/app/index.html
systemctl restart eero-dashboard
echo "✅ Update complete! Dashboard restarted."
UPDATEEOF
chmod +x "$APP_DIR/update.sh"

# --- Step 10: Start services ---
log "🚀 Starting services..."
systemctl daemon-reload
systemctl enable eero-dashboard
systemctl start eero-dashboard

systemctl enable nginx
systemctl restart nginx

# --- Step 11: Wait and verify ---
log "⏳ Waiting for services to start..."
sleep 5

if systemctl is-active --quiet eero-dashboard; then
    log "✅ eero-dashboard service is running"
else
    err "eero-dashboard service failed to start"
    journalctl -u eero-dashboard --no-pager -n 20
    exit 1
fi

if systemctl is-active --quiet nginx; then
    log "✅ nginx is running"
else
    err "nginx failed to start"
    exit 1
fi

# Test HTTP
if curl -sf http://localhost/ > /dev/null 2>&1; then
    log "✅ HTTP health check passed"
else
    warn "HTTP check failed — service may still be starting"
fi

# --- Done ---
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "============================================="
echo -e "${GREEN}✅ MiniRack Dashboard installed successfully!${NC}"
echo "============================================="
echo ""
echo "  🌐 Dashboard:  http://$PI_IP"
echo "  📁 App dir:    $APP_DIR"
echo "  📋 Logs:       $APP_DIR/logs/"
echo "  🔄 Update:     sudo $APP_DIR/update.sh"
echo ""
echo "  Service commands:"
echo "    sudo systemctl status eero-dashboard"
echo "    sudo systemctl restart eero-dashboard"
echo "    sudo journalctl -u eero-dashboard -f"
echo ""
echo "  Next: Open http://$PI_IP in your browser,"
echo "  click the π button, and add your networks."
echo "============================================="
