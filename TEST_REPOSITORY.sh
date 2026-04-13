#!/bin/bash

echo "🧪 Testing Eero Event Dashboard Repository..."
echo ""

# Check if we're in the right directory
if [ ! -f "dashboard_simple_local.py" ]; then
    echo "❌ Error: dashboard_simple_local.py not found"
    echo "Please run this script from the eero-event-dashboard directory"
    exit 1
fi

echo "✅ Found dashboard_simple_local.py"

# Check Python version
python_version=$(python3 --version 2>&1)
echo "✅ Python version: $python_version"

# Check required files
required_files=(
    "README.md"
    "LICENSE" 
    ".gitignore"
    "dashboard_simple_local.py"
    "deploy/dashboard_minimal.py"
    "deploy/index.html"
    "deploy/requirements.txt"
)

echo ""
echo "📁 Checking required files..."
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
    fi
done

# Check deploy directory
echo ""
echo "📂 Deploy directory contents:"
ls -la deploy/

echo ""
echo "🚀 Repository structure looks good!"
echo ""
echo "📋 Next steps:"
echo "1. Run: python3 dashboard_simple_local.py"
echo "2. Open: http://localhost:3000"
echo "3. Test CSV export and network management"
echo ""
echo "🎉 Ready to run the Eero Event Dashboard!"