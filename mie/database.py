"""
MIE Database Layer - SQLite + JSON Runtime

Estructura de memoria:
├─ observations: Todas las observaciones (append-only)
├─ hypotheses: Hipótesis activas + archive
├─ experiments: Log de experimentos
├─ dialogue_memory: Historial de diálogos
├─ user_feedback: Feedback marcado
└─ relationships: Correlaciones detectadas
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class MIEDatabase:
    def __init__(self, db_path: str = "mie.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.init_db()

    def init_db(self):
        """Inicializa la base de datos con tablas"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        # Tabla: observations (append-only)
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

        # Tabla: hypotheses
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

        # Tabla: experiments (append-only log)
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

        # Tabla: dialogue_memory
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

        # Tabla: user_feedback
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                observation_id TEXT,
                feedback_type TEXT,
                context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla: relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                asset1 TEXT NOT NULL,
                asset2 TEXT NOT NULL,
                correlation REAL,
                context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla: learning_logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def add_observation(self, asset: str, observation_type: str, value: float,
                       context: str = None, flags: str = None) -> int:
        """Agrega una observación (append-only)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO observations
            (timestamp, source, asset, observation_type, value, context, flags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            'binance',
            asset,
            observation_type,
            value,
            context,
            flags
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_observations(self, asset: str, lookback_hours: int = 24,
                        observation_type: str = None) -> List[Dict]:
        """Obtiene observaciones recientes"""
        cursor = self.conn.cursor()
        query = '''
            SELECT * FROM observations
            WHERE asset = ? AND datetime(timestamp) > datetime('now', '-' || ? || ' hours')
        '''
        params = [asset, lookback_hours]

        if observation_type:
            query += ' AND observation_type = ?'
            params.append(observation_type)

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_hypothesis(self, hypothesis_id: str, text: str, born_from: str,
                     priority: float = 0.5) -> None:
        """Agrega una nueva hipótesis"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO hypotheses
            (hypothesis_id, text, born_date, born_from, priority)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            hypothesis_id,
            text,
            datetime.utcnow().isoformat(),
            born_from,
            priority
        ))
        self.conn.commit()

    def update_hypothesis(self, hypothesis_id: str, **kwargs) -> None:
        """Actualiza hipótesis (solo campos permitidos)"""
        cursor = self.conn.cursor()
        allowed_fields = ['status', 'confidence', 'priority', 'decision', 'notes', 'observation_count']

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return

        updates['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
        values = list(updates.values()) + [hypothesis_id]

        cursor.execute(f'UPDATE hypotheses SET {set_clause} WHERE hypothesis_id = ?', values)
        self.conn.commit()

    def get_active_hypotheses(self) -> List[Dict]:
        """Obtiene hipótesis activas"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM hypotheses
            WHERE status IN ('awaiting_validation', 'testing')
            ORDER BY priority DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def add_experiment(self, exp_id: str, hypothesis_id: str, description: str,
                      test_design: Dict) -> None:
        """Agrega experimento (append-only)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO experiments
            (exp_id, hypothesis_id, created_date, description, test_design)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            exp_id,
            hypothesis_id,
            datetime.utcnow().isoformat(),
            description,
            json.dumps(test_design)
        ))
        self.conn.commit()

    def update_experiment(self, exp_id: str, results: Dict, analysis: Dict,
                         classification: str, decision: str) -> None:
        """Actualiza resultados de experimento"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE experiments
            SET results = ?, analysis = ?, classification = ?, decision = ?
            WHERE exp_id = ?
        ''', (
            json.dumps(results),
            json.dumps(analysis),
            classification,
            decision,
            exp_id
        ))
        self.conn.commit()

    def add_dialogue(self, user_message: str, mie_response: str, context: str = None) -> None:
        """Agrega entrada de diálogo"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO dialogue_memory
            (timestamp, user_message, mie_response, context)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            user_message,
            mie_response,
            context
        ))
        self.conn.commit()

    def add_learning_log(self, log_type: str, content: str) -> None:
        """Agrega log de aprendizaje (daily/weekly)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO learning_logs
            (log_type, timestamp, content)
            VALUES (?, ?, ?)
        ''', (
            log_type,
            datetime.utcnow().isoformat(),
            content
        ))
        self.conn.commit()

    def get_learning_logs(self, log_type: str = None, days: int = 7, limit: int = 5) -> List[Dict]:
        """Obtiene logs de aprendizaje recientes"""
        cursor = self.conn.cursor()

        if log_type:
            cursor.execute('''
                SELECT * FROM learning_logs
                WHERE log_type = ? AND datetime(timestamp) > datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (log_type, days, limit))
        else:
            cursor.execute('''
                SELECT * FROM learning_logs
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (days, limit))

        return [dict(row) for row in cursor.fetchall()]

    def add_user_feedback(self, feedback_type: str, context: str = None) -> None:
        """Agrega feedback del usuario"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO user_feedback
            (timestamp, feedback_type, context)
            VALUES (?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            feedback_type,
            context
        ))
        self.conn.commit()

    def close(self):
        """Cierra conexión"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def count_observations(self, asset: str = None, lookback_hours: int = 24) -> int:
        """Cuenta las observaciones en el periodo especificado."""
        cursor = self.conn.cursor()
        if asset:
            cursor.execute('''
                SELECT COUNT(*) FROM observations
                WHERE asset = ? AND datetime(timestamp) > datetime('now', '-' || ? || ' hours')
            ''', (asset, lookback_hours))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM observations
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
            ''', (lookback_hours,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def count_dialogue_entries(self, lookback_hours: int = 24) -> int:
        """Count dialogue entries in lookback window."""
        cursor = self.conn.cursor()
        since = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat()
        cursor.execute("SELECT COUNT(*) as count FROM dialogue_memory WHERE timestamp > ?", (since,))
        row = cursor.fetchone()
        return row["count"] if row else 0

    def count_feedback_entries(self, lookback_hours: int = 24) -> int:
        """Count user feedback entries in lookback window."""
        cursor = self.conn.cursor()
        since = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat()
        cursor.execute("SELECT COUNT(*) as count FROM user_feedback WHERE timestamp > ?", (since,))
        row = cursor.fetchone()
        return row["count"] if row else 0

