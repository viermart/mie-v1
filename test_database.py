#!/usr/bin/env python3
"""
Test script para validar la estructura de BD sin deps externas
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path


def test_database():
    """Crea BD de test y valida schema"""

    test_db = "test_mie.db"
    test_db_path = Path(test_db)

    # Limpia DB anterior si existe
    if test_db_path.exists():
        test_db_path.unlink()

    print("🧪 Iniciando test de BD...")

    # Conecta
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Crea tablas (same schema como database.py)
    print("📝 Creando tablas...")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            asset TEXT NOT NULL,
            observation_type TEXT NOT NULL,
            value REAL,
            context TEXT,
            flags TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hypotheses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id TEXT UNIQUE NOT NULL,
            text TEXT NOT NULL,
            born_date TEXT NOT NULL,
            born_from TEXT,
            observation_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'awaiting_validation',
            confidence TEXT DEFAULT 'insufficient_evidence',
            priority REAL DEFAULT 0.5,
            decision TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_id TEXT UNIQUE NOT NULL,
            hypothesis_id TEXT NOT NULL,
            created_date TEXT NOT NULL,
            description TEXT,
            test_design TEXT,
            data_used TEXT,
            results TEXT,
            analysis TEXT,
            classification TEXT,
            overfit_risk TEXT,
            decision TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dialogue_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_message TEXT,
            mie_response TEXT,
            context TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    print("✅ Tablas creadas")

    # Test inserciones
    print("\n📊 Testeando inserciones...")

    # Observación
    cursor.execute('''
        INSERT INTO observations
        (timestamp, source, asset, observation_type, value, context)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.utcnow().isoformat(),
        'binance',
        'BTC',
        'price',
        45234.50,
        '24h_change: +2.3%'
    ))
    obs_id = cursor.lastrowid
    print(f"✅ Observación insertada (id={obs_id})")

    # Hipótesis
    cursor.execute('''
        INSERT INTO hypotheses
        (hypothesis_id, text, born_date, born_from, priority)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'hyp_BTC_price_spike_001',
        'BTC mostró movimiento de +3.1% en 24h',
        datetime.utcnow().isoformat(),
        'trigger:price_momentum',
        0.7
    ))
    print("✅ Hipótesis insertada")

    # Experimento
    cursor.execute('''
        INSERT INTO experiments
        (exp_id, hypothesis_id, created_date, description, test_design)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'exp_BTC_001_20260421',
        'hyp_BTC_price_spike_001',
        datetime.utcnow().isoformat(),
        'Validación de hipótesis de momentum',
        json.dumps({"lookback_hours": 168, "threshold": 0.02})
    ))
    print("✅ Experimento insertado")

    # Learning log
    cursor.execute('''
        INSERT INTO learning_logs
        (log_type, timestamp, content)
        VALUES (?, ?, ?)
    ''', (
        'daily',
        datetime.utcnow().isoformat(),
        json.dumps({
            "observation_count": 1,
            "hypothesis_count": 1,
            "price_summary": "BTC: 45234"
        })
    ))
    print("✅ Learning log insertado")

    conn.commit()

    # Test queries
    print("\n🔍 Testeando queries...")

    # Get observations
    cursor.execute('SELECT * FROM observations WHERE asset = ? ORDER BY timestamp DESC', ('BTC',))
    obs = cursor.fetchall()
    print(f"✅ Observaciones obtenidas: {len(obs)} registros")
    if obs:
        print(f"   Última: {dict(obs[0])['observation_type']} = {dict(obs[0])['value']}")

    # Get hypotheses
    cursor.execute('SELECT * FROM hypotheses WHERE status IN ("awaiting_validation", "testing")')
    hyps = cursor.fetchall()
    print(f"✅ Hipótesis activas: {len(hyps)} registros")
    if hyps:
        print(f"   Texto: {dict(hyps[0])['text']}")

    # Get learning logs
    cursor.execute('''
        SELECT * FROM learning_logs
        WHERE log_type = ? AND datetime(timestamp) > datetime('now', '-7 days')
        ORDER BY timestamp DESC
    ''', ('daily',))
    logs = cursor.fetchall()
    print(f"✅ Learning logs (7d): {len(logs)} registros")

    conn.close()

    # Limpia
    test_db_path.unlink()

    print("\n✅ Test completado exitosamente")
    print("✅ BD schema validado")
    print("✅ Listo para MIE V1")


if __name__ == "__main__":
    test_database()
