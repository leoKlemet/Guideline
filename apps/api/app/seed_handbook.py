import os
import time
import json
import sqlite3
from pypdf import PdfReader
from .retrieval import chunk_text_to_chunks, uid

def seed_handbook(
    conn: sqlite3.Connection,
    pdf_path: str,
    *,
    policy_key="employee_handbook",
    effective_date="2025-03-01",
    access="internal",
    tags=None,
    reset=False
):
    if tags is None:
        tags = ["hr", "handbook", "benefits"]

    print(f"Seeding handbook from: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return

    cursor = conn.cursor()

    # Reset logic
    if reset:
        print(f"Resetting existing handbook entries for key: {policy_key}")
        # Find doc ids to delete chunks
        cursor.execute("SELECT id FROM documents WHERE policy_key = ?", (policy_key,))
        rows = cursor.fetchall()
        doc_ids = [r[0] for r in rows]
        
        if doc_ids:
            placeholders = ','.join(['?'] * len(doc_ids))
            cursor.execute(f"DELETE FROM chunks WHERE doc_id IN ({placeholders})", doc_ids)
            cursor.execute("DELETE FROM documents WHERE policy_key = ?", (policy_key,))
            conn.commit()

    # Check if exists (if not reset)
    cursor.execute("SELECT id FROM documents WHERE policy_key = ?", (policy_key,))
    if cursor.fetchone():
        print("Handbook already seeded. Use --reset-handbook to overwrite.")
        return

    # Read PDF
    reader = PdfReader(pdf_path)
    full_text = ""
    
    # We will simply extract all text for now to pass to the chunker, 
    # but we could carry page numbers if we modified chunk_text_to_chunks.
    # For this prototype, let's extract by page and append.
    
    print(f"Processing {len(reader.pages)} pages...")
    
    doc_id = uid("doc")
    now = int(time.time() * 1000)
    
    # 1. Insert Document
    doc_data = (
        doc_id,
        "Employee Handbook (March 2025)",
        policy_key,
        effective_date,
        access,
        json.dumps(tags),
        now
    )
    cursor.execute("""
        INSERT INTO documents (id, title, policy_key, effective_date, access, tags_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, doc_data)

    total_chunks = 0
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        # Optional: Skip Table of Contents
        if "Table of Contents" in text:
            print(f"Skipping page {i+1} (Table of Contents)")
            continue

        # Chunk logic customization: 
        # We want to preserve page number in citations.
        # The current chunk_text_to_chunks sets page_start=1 fixed.
        # We can either modify retrieval.py or manually chunk here.
        # Let's manually chunk here to support the requirement "page-aware citations".
        
        # Simple split by paragraphs
        parts = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Aggregate parts into chunks of ~1000 chars
        current_chunk = ""
        chunk_idx_on_page = 0
        
        for p in parts:
            if len(current_chunk) + len(p) > 1000:
                # Flush chunk
                c_id = uid("chunk")
                cursor.execute("""
                    INSERT INTO chunks (id, doc_id, chunk_index, type, page_start, page_end, content, access, effective_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c_id, doc_id, total_chunks, "text", i + 1, i + 1, current_chunk, access, effective_date
                ))
                total_chunks += 1
                current_chunk = p
            else:
                current_chunk += "\n\n" + p if current_chunk else p
        
        # Flush remainder
        if current_chunk:
            c_id = uid("chunk")
            cursor.execute("""
                INSERT INTO chunks (id, doc_id, chunk_index, type, page_start, page_end, content, access, effective_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c_id, doc_id, total_chunks, "text", i + 1, i + 1, current_chunk, access, effective_date
            ))
            total_chunks += 1

    conn.commit()
    print(f"Successfully seeded handbook: {doc_id} with {total_chunks} chunks.")
