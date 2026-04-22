#!/bin/bash

# Setup local para MIE V1
# Uso: bash setup_local.sh

echo "🚀 Setup MIE V1 (local development)"

# 1. Crea venv
if [ ! -d "venv" ]; then
    echo "📦 Creando venv..."
    python3 -m venv venv
else
    echo "✅ venv existe"
fi

# 2. Activa venv
echo "🔌 Activando venv..."
source venv/bin/activate

# 3. Instala deps
echo "📚 Instalando dependencias..."
pip install -r requirements.txt

# 4. Copia .env
if [ ! -f ".env" ]; then
    echo "📝 Copiando .env.example → .env"
    cp .env.example .env
    echo "⚠️  Edita .env con tus credenciales (TELEGRAM_TOKEN, etc.)"
else
    echo "✅ .env existe"
fi

# 5. Crea directorio de logs
mkdir -p logs

echo ""
echo "✅ Setup completado"
echo ""
echo "📋 Próximos pasos:"
echo "  1. Edita .env con tus credenciales"
echo "  2. Ejecuta: python main.py"
echo ""
