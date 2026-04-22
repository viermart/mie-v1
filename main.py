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

    # Genera runtime ID único para esta instancia
    import uuid
    runtime_id = str(uuid.uuid4())[:8]

    # Log de versión y diagnóstico
    print("\n" + "="*60)
    print("🚀 MIE V1 - Market Intelligence Entity")
    print(f"📌 RUNTIME_ID: {runtime_id}")
    print("📌 VERSION: 2.3 - Single Runtime Enforcement")
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

    # Acquire runtime lock - only newest instance processes Telegram
    import time as time_module
    lock_file = Path("mie_runtime.lock")

    print(f"📍 RUNTIME_ID: {runtime_id}")
    print(f"🔒 Adquiriendo runtime lock...")

    # Write our runtime ID and timestamp
    with open(lock_file, "w") as f:
        f.write(f"{runtime_id}:{time_module.time()}")

    # Wait a moment and re-read - if our ID is still there, we're the active instance
    time_module.sleep(2)
    with open(lock_file, "r") as f:
        active_id, _ = f.read().split(":")

    if active_id != runtime_id:
        print(f"❌ LOCKED OUT: Another runtime ({active_id}) is active. Exiting.")
        sys.exit(0)

    print(f"✅ RUNTIME LOCK ACQUIRED: {runtime_id} is active")

    # Inicia
    orchestrator.run()


if __name__ == "__main__":
    main()
