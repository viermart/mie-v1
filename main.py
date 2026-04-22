#!/usr/bin/env python3
"""
MIE V1 - Market Intelligence Entity
Bootstrap phase: Pure observation, reflection, and learning

VERSION: 2.1 - Debug System Ready
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

from mie.orchestrator import MIEOrchestrator


def main():
    # Carga variables de entorno
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("⚠️  .env no encontrado - usando variables de entorno del sistema")

    # Obtiene configuración
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    db_path = os.getenv("DB_PATH", "mie.db")

    # Log de versión
    print("\n" + "="*60)
    print("🚀 MIE V1 - Market Intelligence Entity")
    print("📌 MARKER: MIE_MARKER_2026_04_22_X1")
    print("📌 VERSION: 2.1 - Debug System Enabled")
    print("   Available commands: /debug, /debug btc, /debug eth, /debug all")
    print("="*60 + "\n")

    # Inicializa orquestador
    orchestrator = MIEOrchestrator(
        db_path=db_path,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id
    )

    # Inicia
    orchestrator.run()


if __name__ == "__main__":
    main()
