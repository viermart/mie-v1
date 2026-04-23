#!/usr/bin/env python3
"""
Setup environment file from system environment variables.
This allows Railway to pass variables that get written to .env at runtime.
"""

import os
from pathlib import Path

def setup_env_file():
    """Create .env file from environment variables.
    ALWAYS regenerate - this ensures Railway's injected variables are used.
    """
    env_path = Path(__file__).parent / ".env"

    # Variables a copiar desde el entorno
    vars_to_copy = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ANTHROPIC_API_KEY",
        "DATABASE_URL",
        "DB_PATH",
        "HOST",
        "PORT"
    ]

    # Crear .env con las variables disponibles (SIEMPRE, para que Railway pueda inyectar)
    env_content = "# MIE V1 - Generated at runtime\n\n"

    for var in vars_to_copy:
        value = os.getenv(var)
        if value:
            env_content += f"{var}={value}\n"

    if env_content.count("\n") > 2:
        # Solo escribir si hay variables reales
        env_path.write_text(env_content)
        print(f"✅ Archivo .env regenerado con {len([v for v in vars_to_copy if os.getenv(v)])} variables")
    else:
        print("ℹ️  No hay variables de entorno para generar .env")

if __name__ == "__main__":
    setup_env_file()
