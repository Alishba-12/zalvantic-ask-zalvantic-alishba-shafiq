"""Tiny SQLite log. Stores only the anonymised question, the outcome and the time. No IP, no user id."""
import os
import sqlite3
import time

DB_PATH = os.environ.get("ASKZ_DB", "data/questions.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS questions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, question TEXT, outcome TEXT)"
    )
    return con


def log_question(question: str, outcome: str) -> None:
    """outcome is one of: answered, unanswered, refused"""
    con = _conn()
    with con:
        con.execute(
            "INSERT INTO questions (ts, question, outcome) VALUES (?, ?, ?)",
            (int(time.time()), question, outcome),
        )
    con.close()


def unanswered():
    con = _conn()
    rows = con.execute(
        "SELECT question, COUNT(*) AS n, MAX(ts) AS last FROM questions "
        "WHERE outcome = 'unanswered' GROUP BY question ORDER BY n DESC, last DESC"
    ).fetchall()
    con.close()
    return rows
