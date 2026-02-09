#!/bin/bash

echo "🚀 KE-WP Mapping Application Startup"
echo "====================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "📋 Setup required:"
    echo "1. Copy the template: cp .env.example .env"
    echo "2. Edit .env with your GitHub OAuth credentials"
    echo "3. Get credentials from: https://github.com/settings/developers"
    echo ""
    exit 1
fi

# Source environment variables
set -a
source .env
set +a

# Validate required variables
if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ] || [ -z "$FLASK_SECRET_KEY" ]; then
    echo "❌ Error: Required environment variables missing!"
    echo "Please check your .env file has:"
    echo "  - GITHUB_CLIENT_ID"
    echo "  - GITHUB_CLIENT_SECRET" 
    echo "  - FLASK_SECRET_KEY"
    exit 1
fi

echo "✅ Configuration loaded"
echo "🌐 Starting server on http://localhost:${PORT:-5000}"
echo "🔑 GitHub OAuth configured"
echo "👤 Admin users: ${ADMIN_USERS:-none}"
echo ""
echo "📝 Press CTRL+C to stop"
echo ""

# Start the application
python app.py