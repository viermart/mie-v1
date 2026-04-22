#!/bin/bash

echo "=========================================="
echo "🚀 MIE V1 STARTUP"
echo "=========================================="
echo ""
echo "📊 Checking Environment Variables:"
echo "  TELEGRAM_TOKEN: ${TELEGRAM_TOKEN:0:20}..."
echo "  TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."
echo ""
echo "📂 Checking Files:"
if [ -f ".env" ]; then
    echo "  ✅ .env exists"
    echo "  First 100 chars: $(head -c 100 .env)"
else
    echo "  ❌ .env does not exist"
fi
echo ""
echo "=========================================="
echo "Starting MIE..."
echo "=========================================="
echo ""

python -u main.py
