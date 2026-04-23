#!/usr/bin/env python3
"""
Smoke test: Commands + Dialogue over unified context
Test the 5 cases specified:
1. /btc
2. /market
3. "ves algo?"
4. "como está btc?"
5. /validation
"""

import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except:
    pass

sys.path.insert(0, str(Path(__file__).parent))

def test_unified_interaction():
    """Test commands and dialogue reading from same DB"""
    print("\n" + "="*70)
    print("UNIFIED INTERACTION TEST")
    print("="*70 + "\n")

    # Setup
    from mie.database import MIEDatabase
    from mie.command_handler import CommandHandler
    from mie.dialogue import DialogueHandler
    from mie.unified_context import UnifiedContextProvider
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TEST")

    db = MIEDatabase("mie.db")

    # First, make sure we have some data
    logger.info("1️⃣ Checking DB state...")
    btc_obs = db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
    eth_obs = db.get_observations(asset="ETH", lookback_hours=24, observation_type="price")
    logger.info(f"   BTC observations: {len(btc_obs) if btc_obs else 0}")
    logger.info(f"   ETH observations: {len(eth_obs) if eth_obs else 0}")

    if not btc_obs or not eth_obs:
        logger.error("❌ No data in DB - run fast_loop first")
        return False

    # Test UnifiedContextProvider
    logger.info("\n2️⃣ Testing UnifiedContextProvider...")
    context_provider = UnifiedContextProvider(db, logger)
    market_context = context_provider.get_market_context()
    if "error" in market_context:
        logger.error(f"❌ Context error: {market_context['error']}")
        return False
    logger.info(f"   ✅ Got market context: BTC ${market_context['btc']['price']:.2f}")

    # Initialize handlers
    logger.info("\n3️⃣ Initializing handlers...")
    commands = CommandHandler(db, logger)
    dialogue = DialogueHandler(db, logger)
    logger.info("   ✅ Handlers initialized")

    # Test cases
    test_cases = [
        ("command", "/btc", commands),
        ("command", "/market", commands),
        ("dialogue", "ves algo?", dialogue),
        ("dialogue", "como está btc?", dialogue),
        ("command", "/validation", commands),
    ]

    logger.info("\n4️⃣ Running test cases...\n")

    all_passed = True
    for i, (test_type, input_text, handler) in enumerate(test_cases, 1):
        try:
            logger.info(f"   Test {i}: {test_type.upper()} - '{input_text}'")

            if test_type == "command":
                response = handler.handle_command(input_text, "test_user")
            else:  # dialogue
                response = handler.handle_message(input_text, "test_user")

            if response:
                logger.info(f"   ✅ Response (first 100 chars): {response[:100]}...")
            else:
                logger.error(f"   ❌ Empty response")
                all_passed = False

        except Exception as e:
            logger.error(f"   ❌ Error: {e}", exc_info=True)
            all_passed = False

    logger.info("\n" + "="*70)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
        logger.info("="*70)
        return True
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("="*70)
        return False

if __name__ == "__main__":
    success = test_unified_interaction()
    sys.exit(0 if success else 1)
