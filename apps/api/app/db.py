import sqlite3
import os
from contextlib import contextmanager

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "../data/guideline.db")

def get_db_path():
    return os.getenv("GUIDELINE_DB_PATH", DEFAULT_DB_PATH)

def connect():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        policy_key TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        access TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        created_at INTEGER NOT NULL
    );
    """)

    # Chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        type TEXT NOT NULL,
        page_start INTEGER NOT NULL,
        page_end INTEGER NOT NULL,
        content TEXT NOT NULL,
        access TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES documents(id)
    );
    """)

    # Review Queue table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_queue (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL,
        draft_answer TEXT,
        draft_citations_json TEXT NOT NULL,
        final_answer TEXT,
        created_at INTEGER NOT NULL,
        resolved_at INTEGER
    );
    """)

    # Schedule Config table (singleton)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        json_blob TEXT NOT NULL,
        updated_at INTEGER NOT NULL
    );
    """)

    conn.commit()
    return conn

def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
