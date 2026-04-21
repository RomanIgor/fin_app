"""
Strat de persistență SQLite.
DB se creează automat la primul rulaj în data/finanzen.db.
"""
import sqlite3
import pandas as pd
from pathlib import Path
import hashlib

DB_PATH = Path("data") / "finanzen.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creează tabelele dacă nu există."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            merchant TEXT DEFAULT '',
            amount REAL NOT NULL,
            category TEXT NOT NULL DEFAULT 'Sonstiges',
            raw_text TEXT,
            tx_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category)")
    
    # Migration: adaugă coloana merchant la DB-uri existente
    try:
        cur.execute("ALTER TABLE transactions ADD COLUMN merchant TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # coloana există deja
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            category TEXT PRIMARY KEY,
            monthly_limit REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            keyword TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def _tx_hash(date: str, description: str, amount: float) -> str:
    """Hash unic pentru a preveni duplicatele la re-import."""
    s = f"{date}|{description[:100]}|{amount:.2f}"
    return hashlib.md5(s.encode()).hexdigest()


def insert_transactions(df: pd.DataFrame) -> tuple[int, int]:
    """
    Inserează tranzacții, ignorând duplicatele (bazat pe hash).
    Returnează (n_inserate, n_duplicate).
    """
    conn = get_conn()
    cur = conn.cursor()
    
    n_inserted = 0
    n_duplicates = 0
    
    for _, row in df.iterrows():
        h = _tx_hash(str(row['date']), row['description'], row['amount'])
        try:
            cur.execute("""
                INSERT INTO transactions (date, description, merchant, amount, category, raw_text, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row['date']),
                row['description'],
                row.get('merchant', ''),
                float(row['amount']),
                row.get('category', 'Sonstiges'),
                row.get('raw_text', ''),
                h
            ))
            n_inserted += 1
        except sqlite3.IntegrityError:
            n_duplicates += 1
    
    conn.commit()
    conn.close()
    return n_inserted, n_duplicates


def get_transactions(date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """Returnează toate tranzacțiile (sau filtrate pe perioadă)."""
    conn = get_conn()
    query = "SELECT id, date, description, merchant, amount, category FROM transactions"
    params = []
    conditions = []
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date DESC, id DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def update_category(tx_id: int, new_category: str):
    conn = get_conn()
    conn.execute("UPDATE transactions SET category = ? WHERE id = ?", (new_category, tx_id))
    conn.commit()
    conn.close()


def get_budgets() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT category, monthly_limit FROM budgets").fetchall()
    conn.close()
    return {r['category']: r['monthly_limit'] for r in rows}


def upsert_budget(category: str, limit: float):
    conn = get_conn()
    conn.execute("""
        INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)
        ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit,
        updated_at = CURRENT_TIMESTAMP
    """, (category, limit))
    conn.commit()
    conn.close()


def delete_budget(category: str):
    conn = get_conn()
    conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
    conn.commit()
    conn.close()


def get_rules() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT keyword, category FROM rules").fetchall()
    conn.close()
    return {r['keyword']: r['category'] for r in rows}


def upsert_rule(keyword: str, category: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO rules (keyword, category) VALUES (?, ?)
        ON CONFLICT(keyword) DO UPDATE SET category = excluded.category
    """, (keyword.lower(), category))
    conn.commit()
    conn.close()


def get_monthly_summary() -> pd.DataFrame:
    """Rezumat pe lună și categorie."""
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT 
            strftime('%Y-%m', date) as month,
            category,
            SUM(amount) as total,
            COUNT(*) as n_tx
        FROM transactions
        GROUP BY month, category
        ORDER BY month DESC, total
    """, conn)
    conn.close()
    return df
