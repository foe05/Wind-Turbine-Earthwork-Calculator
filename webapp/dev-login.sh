#!/bin/bash
# 🔧 Development Login Helper
# Get magic link without email server

set -e

echo "🔧 Development Login Helper"
echo "============================"
echo ""

# Check if email is provided
if [ -z "$1" ]; then
    echo "Usage: ./dev-login.sh <email>"
    echo ""
    echo "Example:"
    echo "  ./dev-login.sh test@example.com"
    echo ""
    exit 1
fi

EMAIL=$1
API_GATEWAY="http://localhost:8000"

echo "📧 Email: $EMAIL"
echo ""

# Step 1: Request magic link
echo "Step 1: Requesting magic link..."
REQUEST_RESPONSE=$(curl -s -X POST "$API_GATEWAY/auth/request-login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\"}")

echo "✅ Response: $REQUEST_RESPONSE"
echo ""

# Step 2: Get magic link from dev endpoint
echo "Step 2: Fetching magic link from dev endpoint..."
DEV_RESPONSE=$(curl -s -X GET "$API_GATEWAY/auth/dev/magic-links/$EMAIL")

echo "📋 Response:"
echo "$DEV_RESPONSE" | jq '.'
echo ""

# Extract the URL
MAGIC_LINK=$(echo "$DEV_RESPONSE" | jq -r '.links[0].url // empty')

if [ -n "$MAGIC_LINK" ]; then
    echo "✨ Your Magic Link:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$MAGIC_LINK"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🌐 Open this URL in your browser to login!"
    echo ""

    # Try to open in browser (works on some systems)
    if command -v xdg-open &> /dev/null; then
        read -p "Open in browser now? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            xdg-open "$MAGIC_LINK"
        fi
    fi
else
    echo "❌ No magic link found. Error details:"
    echo "$DEV_RESPONSE" | jq '.'
fi
