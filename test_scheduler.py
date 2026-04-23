#!/usr/bin/env python3
"""
Test que el scheduler está funcionando correctamente.
Ejecuta solo fast_loop una sola vez para verificar que funciona.
"""

import os
import sys
from pathlib import Path

# Try to load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))

from mie.orchestrator import MIEOrchestrator

def main():
    print("\n" + "="*70)
    print("TEST: Ejecutar fast_loop UNA SOLA VEZ")
    print("="*70 + "\n")

    # Obtiene credenciales
    telegram_token = os.getenv("TELEGRAM_TOKEN", "dummy")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "dummy")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"TELEGRAM_TOKEN: {telegram_token[:20]}...")
    print(f"TELEGRAM_CHAT_ID: {telegram_chat_id}")
    print(f"ANTHROPIC_API_KEY: {'✅' if anthropic_api_key else '❌'}\n")

    # Inicializa orchestrator
    orchestrator = MIEOrchestrator(
        db_path="mie.db",
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        anthropic_api_key=anthropic_api_key
    )

    # Ejecuta fast_loop una sola vez
    print("\nEjecutando fast_loop...\n")
    orchestrator.fast_loop()

    print("\n✅ Test completado")

if __name__ == "__main__":
    main()
