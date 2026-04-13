#!/bin/bash
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
