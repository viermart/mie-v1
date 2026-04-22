#!/usr/bin/env python3
"""
MIE V1 - Market Intelligence Entity
Bootstrap phase: Pure observation, reflection, and learning

VERSION: 2.2 - Railway Redeploy with Claude API
- Debug commands: /debug, /debug btc, /debug eth, /debug all, /debug status
- 4-stage pipeline diagnostics
- Immediate data ingestion on startup
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Añade mie al path
sys.path.insert(0, str(Path(__file__).parent))

from setup_env import setup_env_file
from validate_env import validate_env
from mie.orchestrator import MIEOrchestrator


def main():
    # PRIMERO: Setup - generar .env desde variables de sistema (para Railway)
    setup_env_file()

    # SEGUNDO: Carga variables de entorno desde el .env generado - ANTES de imports que las usen
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print("✅ Archivo .env cargado correctamente")
        # Verificar que las variables están disponibles
        print(f"  • ANTHROPIC_API_KEY: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
        print(f"  • TELEGRAM_TOKEN: {'✅' if os.getenv('TELEGRAM_TOKEN') else '❌'}")
        print(f"  • TELEGRAM_CHAT_ID: {'✅' if os.getenv('TELEGRAM_CHAT_ID') else '❌'}")
    else:
        print("⚠️  .env no encontrado - usando solo variables de entorno del sistema")

    # TERCERO: Validar variables de entorno después de cargarlas
    if not validate_env():
        sys.exit(1)

    # Obtiene configuración
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    db_path = os.getenv("DB_PATH", "mie.db")

    # Log de versión y diagnóstico
    print("\n" + "="*60)
    print("🚀 MIE V1 - Market Intelligence Entity")
    print("📌 MARKER: MIE_MARKER_2026_04_22_X2")
    print("📌 VERSION: 2.2 - Railway Redeploy with Claude API")
    print("\n🔍 DIAGNÓSTICO DE VARIABLES:")
    print(f"  • TELEGRAM_TOKEN: {'✅ Configurada' if telegram_token else '❌ NO CONFIGURADA'}")
    print(f"  • TELEGRAM_CHAT_ID: {'✅ Configurada' if telegram_chat_id else '❌ NO CONFIGURADA'}")
    print(f"  • ANTHROPIC_API_KEY: {'✅ Configurada' if anthropic_api_key else '❌ NO CONFIGURADA'}")
    print(f"  • DB_PATH: {db_path}")
    sys.stdout.flush()
    print("\n" + "="*60 + "\n")

    # Inicializa orquestador - PASANDO LA API KEY
    orchestrator = MIEOrchestrator(
        db_path=db_path,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        anthropic_api_key=anthropic_api_key
    )

    # Inicia
    orchestrator.run()


if __name__ == "__main__":
    main()
