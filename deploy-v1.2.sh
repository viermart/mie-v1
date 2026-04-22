#!/bin/bash
# Deploy MIE V1.2 to Railway
# Asume que estás dentro de mie-v1 directory

set -e

echo "🚀 MIE V1.2 Deployment Script"
echo "================================"
echo ""

# Check if we're in mie-v1 directory
if [ ! -f "main.py" ] || [ ! -d "mie" ]; then
    echo "❌ Error: Must be run from mie-v1 directory"
    echo "Usage: cd mie-v1 && bash deploy-v1.2.sh"
    exit 1
fi

# Check if we have the new dialogue files
if [ ! -f "mie/dialogue.py" ]; then
    echo "❌ Error: mie/dialogue.py not found"
    echo "V1.2 dialogue module is missing"
    exit 1
fi

echo "✅ V1.2 files detected"
echo ""

# Check git status
echo "📋 Git status:"
git status

echo ""
echo "⚠️  About to commit and push. Continue? (y/n)"
read -r response
if [ "$response" != "y" ]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "📦 Staging changes..."
git add -A

echo "💬 Commit message:"
git commit -m "feat: MIE V1.2 - Dialogue system with Telegram message handling"

echo "⬆️  Pushing to repository..."
git push

echo ""
echo "🚢 Deploying to Railway..."
railway deploy

echo ""
echo "✅ MIE V1.2 deployed successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. Check Railway logs: railway logs"
echo "  2. Send a message to your bot via Telegram"
echo "  3. MIE should respond within 30 seconds"
echo ""
echo "💬 Example queries:"
echo "  • 'como ves el mercado'"
echo "  • 'que aprendiste'"
echo "  • 'hipotesis activas'"
echo "  • 'status'"
echo "  • 'btc'"
echo ""
