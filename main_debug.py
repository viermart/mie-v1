#!/usr/bin/env python3
"""
DEBUG VERSION - Logs EVERYTHING to file + stdout
Helps identify exactly where Railway is failing
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Ensure unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), 'w', buffering=1)

# Open debug log file IMMEDIATELY
debug_log = Path("debug.log")
debug_file = open(debug_log, "a")

def log_debug(msg):
    """Log to both stdout and debug.log with timestamp"""
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    debug_file.write(line + "\n")
    debug_file.flush()

log_debug("="*70)
log_debug("🚀 MIE V1 DEBUG START")
log_debug("="*70)

try:
    log_debug("Step 1: Imports...")
    import requests
    log_debug("  ✅ requests imported")

    # Try to load .env
    try:
        from dotenv import load_dotenv
        log_debug("  ✅ dotenv available")
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            log_debug(f"  ✅ .env found at {env_path}")
            load_dotenv(env_path, override=True)
            log_debug("  ✅ .env loaded")
        else:
            log_debug(f"  ⚠️  .env not found at {env_path}")
    except ImportError:
        log_debug("  ⚠️  dotenv not available (Railway injection)")

    log_debug("\nStep 2: Check environment variables...")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    log_debug(f"  TELEGRAM_TOKEN: {'✅' if telegram_token else '❌ MISSING'}")
    log_debug(f"  TELEGRAM_CHAT_ID: {'✅' if telegram_chat_id else '❌ MISSING'}")
    log_debug(f"  ANTHROPIC_API_KEY: {'✅' if anthropic_api_key else '❌ MISSING'}")

    log_debug("\nStep 3: Setup path...")
    sys.path.insert(0, str(Path(__file__).parent))
    log_debug("  ✅ Path setup complete")

    log_debug("\nStep 4: Import setup_env and validate_env...")
    from setup_env import setup_env_file
    from validate_env import validate_env
    log_debug("  ✅ Imported setup_env and validate_env")

    log_debug("\nStep 5: Setup environment file...")
    setup_env_file()
    log_debug("  ✅ setup_env_file() completed")

    log_debug("\nStep 6: Validate environment...")
    if not validate_env():
        log_debug("  ❌ VALIDATION FAILED")
        sys.exit(1)
    log_debug("  ✅ Environment validated")

    log_debug("\nStep 7: Import MIEOrchestrator...")
    from mie.orchestrator import MIEOrchestrator
    log_debug("  ✅ MIEOrchestrator imported")

    log_debug("\nStep 8: Initialize MIEOrchestrator...")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    db_path = os.getenv("DB_PATH", "mie.db")

    log_debug(f"  Creating orchestrator with db_path={db_path}")
    orchestrator = MIEOrchestrator(
        db_path=db_path,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        anthropic_api_key=anthropic_api_key
    )
    log_debug("  ✅ MIEOrchestrator created")

    log_debug("\nStep 9: Start orchestrator.run()...")
    log_debug("  ⏳ Entering main loop...")
    sys.stdout.flush()
    debug_file.flush()

    # Run for 30 seconds then exit for debugging
    start_time = time.time()
    try:
        while time.time() - start_time < 30:
            orchestrator.schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log_debug("  ⏹️  Interrupted by user")

    log_debug("\n✅ DEBUG SESSION COMPLETE")

except Exception as e:
    import traceback
    log_debug(f"\n❌ FATAL ERROR: {e}")
    log_debug(traceback.format_exc())
    sys.exit(1)

finally:
    debug_file.close()
    log_debug(f"\nDebug log saved to: {debug_log}")
