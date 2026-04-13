#!/bin/bash

# Setup script for new eero-event-dashboard repository
# Run this after creating the GitHub repository

echo "🚀 Setting up Eero Event Dashboard repository..."

# Initialize git if not already done
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
fi

# Add all files
echo "📝 Adding files to git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Eero Event Dashboard v6.8.0

Features:
- Full-height per-network information display
- Clickable Eero Insight links for all network IDs  
- CSV export with comprehensive network and device data
- Real-time multi-network monitoring (up to 6 networks)
- Mobile-responsive design with touch optimization
- Production Eero API authentication
- Device type detection (iOS, Android, Windows, Amazon, Gaming, Streaming)
- Frequency analysis (2.4GHz, 5GHz, 6GHz) per network
- Time range selection (1h to 1 week)
- Secure token storage per network
- AWS Lightsail deployment ready
- Local macOS development support

This is a complete, standalone repository with all working features
from the enhanced MiniRack Dashboard project."

# Set up remote (you'll need to update this URL)
echo "🔗 Setting up remote repository..."
echo "Please update the repository URL in this script, then run:"
echo "git remote add origin https://github.com/Drew-CodeRGV/eero-event-dashboard.git"
echo "git branch -M main"
echo "git push -u origin main"

echo ""
echo "✅ Repository setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Create the repository on GitHub: https://github.com/new"
echo "2. Repository name: eero-event-dashboard"
echo "3. Run the git remote commands shown above"
echo "4. Test locally: python3 dashboard_simple_local.py"
echo "5. Access at: http://localhost:3000"
echo ""
echo "🎉 Your new Eero Event Dashboard repository is ready!"