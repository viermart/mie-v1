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

# Try to load .env if available (optional - Railway injects variables directly)
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Añade mie al path
sys.path.insert(0, str(Path(__file__).parent))

from setup_env import setup_env_file
from validate_env import validate_env
from mie.orchestrator import MIEOrchestrator


def main():
    # PRIMERO: Setup - generar .env desde variables de sistema (para Railway)
    setup_env_file()

    # SEGUNDO: Carga variables de entorno desde el .env generado - ANTES de imports que las usen
    # (solo si dotenv está disponible - en Railway las variables ya están inyectadas)
    env_path = Path(__file__).parent / ".env"
    if DOTENV_AVAILABLE and env_path.exists():
        load_dotenv(env_path, override=True)
        print("✅ Archivo .env cargado correctamente")
        # Verificar que las variables están disponibles
        print(f"  • ANTHROPIC_API_KEY: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
        print(f"  • TELEGRAM_TOKEN: {'✅' if os.getenv('TELEGRAM_TOKEN') else '❌'}")
        print(f"  • TELEGRAM_CHAT_ID: {'✅' if os.getenv('TELEGRAM_CHAT_ID') else '❌'}")
    else:
        print("ℹ️  Usando variables de entorno del sistema (Railway injection o local env)")

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
    import os as os_module
    import socket
    from datetime import datetime

    pid = os_module.getpid()
    hostname = socket.gethostname()
    container_id = os_module.getenv("RAILWAY_DEPLOYMENT_ID", "LOCAL")
    timestamp = datetime.now().isoformat()
    runtime_id = str(uuid.uuid4())[:8]

    # Log de versión y diagnóstico con runtime identifiers
    print("\n" + "="*70)
    print("🚀 MIE V1 - Market Intelligence Entity")
    print(f"📌 PID: {pid} | HOSTNAME: {hostname} | CONTAINER: {container_id[:12]}")
    print(f"📌 RUNTIME_ID: {runtime_id}")
    print(f"📌 STARTUP_TIME: {timestamp}")
    print("📌 VERSION: 2.4 - Dual Runtime Diagnostics & Enforcement")
    print("\n🔍 DIAGNÓSTICO DE VARIABLES:")
    print(f"  • TELEGRAM_TOKEN: {'✅' if telegram_token else '❌'}")
    print(f"  • TELEGRAM_CHAT_ID: {'✅' if telegram_chat_id else '❌'}")
    print(f"  • ANTHROPIC_API_KEY: {'✅' if anthropic_api_key else '❌'}")
    print(f"  • DB_PATH: {db_path}")
    sys.stdout.flush()
    print("="*70 + "\n")

    # Inicializa orquestador - PASANDO LA API KEY
    orchestrator = MIEOrchestrator(
        db_path=db_path,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        anthropic_api_key=anthropic_api_key
    )

    # Enforce single runtime using last_message_id as lock mechanism
    # This prevents two handlers from polling the same updates
    import time as time_module

    print(f"\n🔒 ENFORCING SINGLE RUNTIME...")

    # Strategy: Track which runtime last processed a message
    # The oldest deployment will be locked out automatically after 5 minutes of inactivity
    runtime_marker_file = Path(".runtime_active")

    current_time = time_module.time()

    try:
        if runtime_marker_file.exists():
            with open(runtime_marker_file, "r") as f:
                last_runtime, last_time = f.read().split(":")
                last_time = float(last_time)
                age = current_time - last_time

                # If another runtime has been active in last 10 seconds, exit
                if age < 10 and last_runtime != runtime_id:
                    print(f"❌ SECONDARY RUNTIME DETECTED")
                    print(f"   Active runtime: {last_runtime}")
                    print(f"   Age: {age:.1f}s")
                    print(f"   → Exiting to prevent 409 conflicts")
                    sys.exit(0)

        # Write our runtime as active
        with open(runtime_marker_file, "w") as f:
            f.write(f"{runtime_id}:{current_time}")

        print(f"✅ RUNTIME LOCK ACQUIRED: {runtime_id}")

    except Exception as e:
        print(f"⚠️  Runtime lock error: {e} (continuing anyway)")

    # Inicia
    orchestrator.run()


if __name__ == "__main__":
    main()
