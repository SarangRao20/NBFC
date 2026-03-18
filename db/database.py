"""SQLite Database — persists user sessions, loan applications, and chat history."""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nbfc.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS loan_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            customer_name TEXT,
            loan_type TEXT DEFAULT 'personal',
            principal REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            tenure INTEGER DEFAULT 0,
            emi REAL DEFAULT 0,
            dti_ratio REAL DEFAULT 0,
            credit_score INTEGER DEFAULT 0,
            fraud_score REAL DEFAULT 0,
            decision TEXT DEFAULT 'pending',
            rejection_reasons TEXT DEFAULT '[]',
            sanction_pdf TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            session_label TEXT DEFAULT 'Loan Chat',
            messages TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS uploaded_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_phone TEXT NOT NULL,
            doc_type TEXT,
            original_filename TEXT,
            audit_path TEXT,
            name_extracted TEXT,
            salary_extracted REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            tampered INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ─── Loan Applications ──────────────────────────────────────────────────────────
def save_loan_application(phone: str, name: str, terms: dict, decision: str,
                          dti: float, score: int, fraud: float, reasons: list, pdf: str) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO loan_applications 
        (customer_phone, customer_name, loan_type, principal, rate, tenure, emi,
         dti_ratio, credit_score, fraud_score, decision, rejection_reasons, sanction_pdf)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        phone, name, terms.get("loan_type", "personal"),
        terms.get("principal", 0), terms.get("rate", 0), terms.get("tenure", 0), terms.get("emi", 0),
        dti, score, fraud, decision, json.dumps(reasons), pdf
    ))
    conn.commit()
    app_id = cur.lastrowid
    conn.close()
    return app_id


def get_loan_history(phone: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM loan_applications WHERE customer_phone = ? ORDER BY created_at DESC", (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Chat Sessions ───────────────────────────────────────────────────────────────
def save_chat_session(phone: str, label: str, messages: list) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO chat_sessions (customer_phone, session_label, messages) VALUES (?, ?, ?)",
        (phone, label, json.dumps(messages))
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def update_chat_session(session_id: int, messages: list):
    conn = get_conn()
    conn.execute(
        "UPDATE chat_sessions SET messages = ?, updated_at = ? WHERE id = ?",
        (json.dumps(messages), datetime.now().isoformat(), session_id)
    )
    conn.commit()
    conn.close()


def get_chat_sessions(phone: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, session_label, created_at FROM chat_sessions WHERE customer_phone = ? ORDER BY created_at DESC",
        (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_messages(session_id: int) -> list:
    conn = get_conn()
    row = conn.execute("SELECT messages FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return json.loads(row["messages"]) if row else []


# ─── Document Audit Trail ────────────────────────────────────────────────────────
def save_document_record(phone: str, doc_type: str, filename: str, audit_path: str,
                         name_ext: str, salary_ext: float, confidence: float, tampered: bool):
    conn = get_conn()
    conn.execute("""
        INSERT INTO uploaded_documents 
        (customer_phone, doc_type, original_filename, audit_path, name_extracted, salary_extracted, confidence, tampered)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (phone, doc_type, filename, audit_path, name_ext, salary_ext, confidence, int(tampered)))
    conn.commit()
    conn.close()


def get_document_history(phone: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM uploaded_documents WHERE customer_phone = ? ORDER BY uploaded_at DESC", (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
