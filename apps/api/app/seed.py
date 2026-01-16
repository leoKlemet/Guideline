import json
import time
from .db import init_db
from .retrieval import chunk_text_to_chunks, uid

SEED_POLICY = """Travel Policy (2025)

Allowed Transportation
- Flights: economy is default. Upgrades require manager approval.
- Ground: rideshare allowed for airport transit.

Expense Limits (Table)
| Category | Limit | Notes |
|---|---:|---|
| Meals | $60/day | Itemized receipt required |
| Hotel | $220/night | Exceptions need approval |

Receipts
- All expenses above $25 require a receipt.

Effective Date: 2025-01-01"""

DEFAULT_SCHEDULE = {
  "timezone": "America/New_York",
  "week": [
    { "day": "Monday", "start": "09:00", "end": "17:00", "note": "Focus work" },
    { "day": "Tuesday", "start": "09:00", "end": "17:00" },
    { "day": "Wednesday", "start": "09:00", "end": "17:00", "note": "Team sync 11:00" },
    { "day": "Thursday", "start": "09:00", "end": "17:00" },
    { "day": "Friday", "start": "09:00", "end": "15:00", "note": "Demo / wrap" },
  ],
  "oncall": [{ "from": "2026-01-19", "to": "2026-01-23", "note": "Primary on-call" }],
  "holidays": [{ "date": "2026-01-20", "name": "Company Holiday" }],
}

def seed():
    conn = init_db()
    cursor = conn.cursor()

    # Check if doc exists
    cursor.execute("SELECT id FROM documents WHERE policy_key = ?", ("travel_policy",))
    existing = cursor.fetchone()
    
    if not existing:
        doc_id = uid("doc")
        now = int(time.time() * 1000)
        
        # Insert Doc
        doc_data = (
            doc_id,
            "Travel Policy 2025",
            "travel_policy",
            "2025-01-01",
            "internal",
            json.dumps(["travel", "expenses"]),
            now
        )
        cursor.execute("""
            INSERT INTO documents (id, title, policy_key, effective_date, access, tags_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, doc_data)
        
        # Chunk and Insert Chunks
        chunks = chunk_text_to_chunks(doc_id, SEED_POLICY, "internal", "2025-01-01")
        for c in chunks:
            cursor.execute("""
                INSERT INTO chunks (id, doc_id, chunk_index, type, page_start, page_end, content, access, effective_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c['id'], c['doc_id'], c['chunk_index'], c['type'], c['page_start'], c['page_end'],
                c['content'], c['access'], c['effective_date']
            ))
            
        print(f"Seeded document: {doc_id} with {len(chunks)} chunks.")
    else:
        print("Document already seeded.")

    # Schedule Upsert
    now = int(time.time() * 1000)
    schedule_json = json.dumps(DEFAULT_SCHEDULE)
    
    cursor.execute("INSERT OR REPLACE INTO schedule_config (id, json_blob, updated_at) VALUES (1, ?, ?)", (schedule_json, now))
    print("Seeded schedule config.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()
