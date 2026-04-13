#!/bin/bash
# Remote setup script - runs on the Pi to configure services
set -e

# Create systemd service
cat > /etc/systemd/system/eero-dashboard.service << 'EOF'
[Unit]
Description=MiniRack Eero Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=eero
Group=eero
WorkingDirectory=/opt/eero/app
Environment=PATH=/opt/eero/venv/bin:/usr/bin:/bin
ExecStart=/opt/eero/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 --access-logfile /opt/eero/logs/access.log --error-logfile /opt/eero/logs/error.log dashboard:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx
cat > /etc/nginx/sites-available/eero-dashboard << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/eero-dashboard /etc/nginx/sites-enabled/

# Start everything
systemctl daemon-reload
systemctl enable --now eero-dashboard
systemctl restart nginx

sleep 3

# Verify
echo "---VERIFY---"
systemctl is-active eero-dashboard && echo "DASHBOARD: RUNNING" || echo "DASHBOARD: FAILED"
systemctl is-active nginx && echo "NGINX: RUNNING" || echo "NGINX: FAILED"
curl -s http://localhost:5000/health || echo "HEALTH_5000: FAILED"
echo ""
curl -s http://localhost/health || echo "HEALTH_80: FAILED"
echo ""
echo "SETUP_COMPLETE"
