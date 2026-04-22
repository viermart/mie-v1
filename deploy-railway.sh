#!/bin/bash

# Deploy MIE V1 a Railway
# Requisitos: railway CLI instalado

set -e

echo "🚀 Desplegando MIE V1 a Railway..."
echo ""

# 1. Verifica que railway esté instalado
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI no instalado"
    echo "Instala con: npm install -g @railway/cli"
    exit 1
fi

# 2. Login
echo "📝 Iniciando sesión en Railway..."
railway login

# 3. Inicializa proyecto si no existe
echo "🔧 Inicializando proyecto..."
railway init --no-prompt || true

# 4. Configura variables de entorno
echo "⚙️  Configurando variables de entorno..."
railway variables set TELEGRAM_TOKEN=8406348922:AAEewXECoJATJ-w9QoYvypkuctLg381_S1w
railway variables set TELEGRAM_CHAT_ID=1186281649
railway variables set DB_PATH=mie.db

# 5. Deploy
echo "🚀 Desplegando a Railway..."
railway up

echo ""
echo "✅ Deploy completado"
echo ""
echo "Verificar estado:"
echo "  railway logs"
echo ""
echo "Ver variables:"
echo "  railway variables"
echo ""
echo "MIE V1 está viva en Railway 🎉"

