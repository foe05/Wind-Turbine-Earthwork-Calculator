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
REQUEST_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_GATEWAY/auth/request-login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\"}")

HTTP_STATUS=$(echo "$REQUEST_RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
RESPONSE_BODY=$(echo "$REQUEST_RESPONSE" | sed '/HTTP_STATUS/d')

echo "✅ Response (Status $HTTP_STATUS): $RESPONSE_BODY"

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Error: Request failed with status $HTTP_STATUS"
    echo "💡 Tip: Make sure services are running (docker-compose up -d)"
    exit 1
fi

echo ""

# Step 2: Get magic link from dev endpoint
echo "Step 2: Fetching magic link from dev endpoint..."
DEV_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$API_GATEWAY/auth/dev/magic-links/$EMAIL")

HTTP_STATUS=$(echo "$DEV_RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
RESPONSE_BODY=$(echo "$DEV_RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Error: Dev endpoint returned status $HTTP_STATUS"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo ""
    echo "💡 Troubleshooting:"
    echo "   1. Check if auth service is running: docker-compose ps auth_service"
    echo "   2. Check logs: docker-compose logs -f auth_service"
    echo "   3. Ensure DEBUG=true in environment"
    exit 1
fi

DEV_RESPONSE="$RESPONSE_BODY"

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
