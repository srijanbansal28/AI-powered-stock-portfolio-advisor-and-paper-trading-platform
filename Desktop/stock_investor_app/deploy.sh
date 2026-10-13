#!/bin/bash

# ============================================
#   Investwithsrijan — Firebase Deploy Script
# ============================================

set -e

FIREBASE="/Users/srijan/.local/node_modules/.bin/firebase"
PROJECT_DIR="/Users/srijan/security_system-1/stock_investor_app"

echo ""
echo "🚀 Investwithsrijan — Firebase Hosting Deployer"
echo "==========================================="
echo ""

cd "$PROJECT_DIR"

# Step 1: Check login status
echo "📋 Step 1: Checking Firebase login..."
if ! $FIREBASE projects:list > /dev/null 2>&1; then
  echo "🔑 Not logged in. Opening Google login in browser..."
  $FIREBASE login
fi
echo "✅ Logged in to Firebase!"

# Step 2: Build production bundle
echo ""
echo "📦 Step 2: Building production bundle..."
npm run build
echo "✅ Build complete!"

# Step 3: Deploy to Firebase Hosting
echo ""
echo "☁️  Step 3: Deploying to Firebase Hosting..."
$FIREBASE deploy --only hosting

echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo ""
echo "🌐 Your live app: https://investiq-ai-a1b2c.web.app"
echo ""
echo "📌 IMPORTANT: Add these URLs to Google OAuth authorized origins:"
echo "   https://investiq-ai-a1b2c.web.app"
echo "   https://investiq-ai-a1b2c.firebaseapp.com"
echo ""
