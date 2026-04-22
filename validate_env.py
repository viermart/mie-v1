#!/usr/bin/env python3
"""
Validate environment variables before starting MIE.
This ensures Railway has all required credentials.
"""

import os
import sys

def validate_env():
    """Validate all required environment variables."""
    required = {
        "TELEGRAM_TOKEN": "Token de Telegram para conectar bot",
        "TELEGRAM_CHAT_ID": "Chat ID de Telegram para recibir mensajes",
        "ANTHROPIC_API_KEY": "API key de Claude para respuestas con IA"
    }

    print("\n" + "="*70)
    print("🔍 VALIDACIÓN DE VARIABLES DE ENTORNO")
    print("="*70)

    missing = []
    for var, desc in required.items():
        value = os.getenv(var)
        if value:
            # Show first 10 and last 10 chars
            masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "***"
            print(f"✅ {var:25} = {masked}")
        else:
            print(f"❌ {var:25} = NO CONFIGURADA")
            missing.append((var, desc))

    print("="*70 + "\n")

    if missing:
        print("❌ VARIABLES FALTANTES:")
        for var, desc in missing:
            print(f"   • {var}: {desc}")
        print("\n⚠️  Railway no puede iniciar MIE sin estas variables.")
        print("   Configúralas en el dashboard de Railway y haz redeploy.")
        return False

    print("✅ TODAS LAS VARIABLES ESTÁN CONFIGURADAS")
    print("   MIE está listo para usar Claude API\n")
    return True

if __name__ == "__main__":
    if not validate_env():
        sys.exit(1)
