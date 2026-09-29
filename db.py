"""
Database layer for Setu prototype.
Uses SQLite for zero-setup, serverless persistence.
Initializes tables and seeds synthetic districts from data/districts.csv.
"""

import sqlite3
import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent / "setu.db"
CSV_PATH = Path(__file__).parent / "data" / "districts.csv"


def get_connection():
    """Get a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force_reseed: bool = False):
    """
    Initialize SQLite schema and seed initial synthetic districts if empty.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Districts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS districts (
                name TEXT PRIMARY KEY,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                pop INTEGER NOT NULL,
                complaints INTEGER NOT NULL,
                infra_gap REAL NOT NULL,
                funded INTEGER NOT NULL,
                category TEXT NOT NULL
            )
        """)
        
        # Complaints logging table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                urgency TEXT NOT NULL,
                language_detected TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

        if force_reseed:
            cursor.execute("DELETE FROM districts")
            conn.commit()

        # Seed from CSV if empty
        cursor.execute("SELECT COUNT(*) FROM districts")
        count = cursor.fetchone()[0]
        if count == 0 and CSV_PATH.exists():
            with open(CSV_PATH, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    funded_val = 1 if row["funded"].strip().lower() in ("true", "1", "yes") else 0
                    cursor.execute("""
                        INSERT OR REPLACE INTO districts (name, x, y, pop, complaints, infra_gap, funded, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["name"].strip(),
                        int(row["x"]),
                        int(row["y"]),
                        int(row["pop"]),
                        int(row["complaints"]),
                        float(row["infra_gap"]),
                        funded_val,
                        row["category"].strip()
                    ))
            conn.commit()


def get_all_districts() -> List[Dict[str, Any]]:
    """Retrieve all districts as list of dictionaries."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, x, y, pop, complaints, infra_gap, funded, category FROM districts ORDER BY name")
        rows = cursor.fetchall()
        return [
            {
                "name": row["name"],
                "x": row["x"],
                "y": row["y"],
                "pop": row["pop"],
                "complaints": row["complaints"],
                "infra_gap": row["infra_gap"],
                "funded": bool(row["funded"]),
                "category": row["category"]
            }
            for row in rows
        ]


def get_district(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single district by name (case-insensitive search)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, x, y, pop, complaints, infra_gap, funded, category FROM districts WHERE LOWER(name) = LOWER(?)", (name.strip(),))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "name": row["name"],
            "x": row["x"],
            "y": row["y"],
            "pop": row["pop"],
            "complaints": row["complaints"],
            "infra_gap": row["infra_gap"],
            "funded": bool(row["funded"]),
            "category": row["category"]
        }


def increment_district_complaints(name: str, increment: int = 1) -> bool:
    """Increment complaints for a given district name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE districts 
            SET complaints = complaints + ? 
            WHERE LOWER(name) = LOWER(?)
        """, (increment, name.strip()))
        conn.commit()
        return cursor.rowcount > 0


def insert_complaint(raw_text: str, category: str, location: str, urgency: str, language_detected: str) -> int:
    """Log an incoming citizen complaint and return inserted ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (raw_text, category, location, urgency, language_detected)
            VALUES (?, ?, ?, ?, ?)
        """, (raw_text, category, location, urgency, language_detected))
        conn.commit()
        return cursor.lastrowid
