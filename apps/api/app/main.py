from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import time
from typing import List, Optional

from .db import init_db, get_db
from .schema import (
    HealthResponse, IngestRequest, IngestResponse, Doc, Chunk, ChatRequest, QAAnswer,
    ReviewItem, ResolveReviewRequest, ResolveReviewResponse, ScheduleConfig, ScheduleAskRequest,
    ScheduleAskResponse, GenericOkResponse, Citation
)
from .retrieval import (
    chunk_text_to_chunks, score_chunk, uid, clamp, detect_conflict,
    build_answer, confidence_from_distance
)

import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health", response_model=HealthResponse)
def health():
    return {"ok": True}

@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest, db: sqlite3.Connection = Depends(get_db)):
    doc_id = uid("doc")
    now = int(time.time() * 1000)
    
    # Insert Document
    doc_data = (
        doc_id, req.title, req.policyKey, req.effectiveDate,
        req.access, json.dumps(req.tags), now
    )
    db.execute("""
        INSERT INTO documents (id, title, policy_key, effective_date, access, tags_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, doc_data)
    
    # Process Chunks
    chunks = chunk_text_to_chunks(doc_id, req.content, req.access, req.effectiveDate)
    for c in chunks:
        db.execute("""
            INSERT INTO chunks (id, doc_id, chunk_index, type, page_start, page_end, content, access, effective_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c['id'], c['doc_id'], c['chunk_index'], c['type'], c['page_start'], c['page_end'],
            c['content'], c['access'], c['effective_date']
        ))
        
    db.commit()
    return {"docId": doc_id, "chunksCreated": len(chunks)}

@app.get("/docs", response_model=List[Doc])
def list_docs(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT * FROM documents ORDER BY created_at DESC")
    docs = []
    for row in cursor.fetchall():
        d = dict(row)
        d['tags'] = json.loads(d['tags_json'])
        # Get chunks for this doc
        c_cursor = db.execute("SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index ASC", (d['id'],))
        d['chunks'] = [dict(c) for c in c_cursor.fetchall()]
        
        # CamelCase conversion for response
        d_out = {
            "id": d['id'],
            "title": d['title'],
            "policyKey": d['policy_key'],
            "effectiveDate": d['effective_date'],
            "access": d['access'],
            "tags": d['tags'],
            "created_at": d['created_at'],
            "chunks": [
                {
                    "id": c['id'],
                    "docId": c['doc_id'],
                    "chunkIndex": c['chunk_index'],
                    "type": c['type'],
                    "pageStart": c['page_start'],
                    "pageEnd": c['page_end'],
                    "content": c['content'],
                    "access": c['access'],
                    "effectiveDate": c['effective_date']
                } for c in d['chunks']
            ]
        }
        docs.append(d_out)
    return docs

@app.post("/chat/ask", response_model=QAAnswer)
def ask_policy(req: ChatRequest, db: sqlite3.Connection = Depends(get_db)):
    # Role to Access Level mapping
    allowed_access = []
    if req.role == "public":
        allowed_access = ["public"]
    elif req.role == "internal":
        allowed_access = ["public", "internal"]
    elif req.role == "confidential":
        allowed_access = ["public", "internal", "confidential"]
    elif req.role == "restricted":
        allowed_access = ["public", "internal", "confidential", "restricted"]
    else:
        allowed_access = ["public", "internal"] # Default

    # Prefer newest doc per policyKey
    docs_cursor = db.execute("SELECT id, policy_key, effective_date, title FROM documents")
    newest_by_key = {}
    doc_titles = {}
    
    for row in docs_cursor.fetchall():
        d = dict(row)
        doc_titles[d['id']] = d['title']
        existing = newest_by_key.get(d['policy_key'])
        if not existing or d['effective_date'] > existing['effective_date']:
            newest_by_key[d['policy_key']] = d
            
    # Get all chunks from these newest docs that match access level
    valid_doc_ids = set([d['id'] for d in newest_by_key.values()])
    if not valid_doc_ids:
        # No docs? return empty
        return {
            "answer": "No documents found.",
            "citations": [],
            "confidence": "Low",
            "bestDistance": 1.0,
            "lowConfidence": True,
            "reviewId": None
        }

    placeholders = ','.join(['?'] * len(valid_doc_ids))
    access_placeholders = ','.join(['?'] * len(allowed_access))
    
    query = f"""
        SELECT * FROM chunks 
        WHERE doc_id IN ({placeholders}) 
        AND access IN ({access_placeholders})
    """
    params = list(valid_doc_ids) + allowed_access
    chunks_cursor = db.execute(query, params)
    chunks = [dict(c) for c in chunks_cursor.fetchall()]

    # Score chunks
    scored = []
    for c in chunks:
        dist = score_chunk(req.question, c['content'])
        scored.append({"c": c, "dist": dist})
    
    # Sort by distance asc, take top 6
    scored.sort(key=lambda x: x['dist'])
    top_scored = scored[:6]
    
    # Filter citations < 0.95
    citations = []
    for item in top_scored:
        if item['dist'] < 0.95:
            c = item['c']
            citations.append({
                "chunkId": c['id'],
                "docId": c['doc_id'],
                "docTitle": doc_titles.get(c['doc_id'], "Unknown"),
                "pageStart": c['page_start'],
                "pageEnd": c['page_end'],
                "quote": c['content'][:220], # Summarize quote logic could be better but basic slice as placeholder
                "distance": round(item['dist'], 3)
            })
            
    best_distance = citations[0]['distance'] if citations else 1.0
    confidence = confidence_from_distance(best_distance)
    
    # Conflict detection
    conflict = detect_conflict(citations, req.question)
    
    not_found = len(citations) == 0 or best_distance >= 0.9
    low_confidence = not_found or best_distance > 0.5 or conflict
    
    answer = build_answer(req.question, citations, req.role)
    
    review_id = None
    if low_confidence:
        reason = "not_found" if not_found else "conflict" if conflict else "low_confidence"
        review_id = uid("rev")
        now = int(time.time() * 1000)
        
        draft_answer = None if not_found else answer
        
        db.execute("""
            INSERT INTO review_queue (id, question, reason, status, draft_answer, draft_citations_json, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            review_id, req.question, reason, "open", draft_answer, json.dumps(citations), now, None
        ))
        db.commit()
        
    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "bestDistance": best_distance,
        "lowConfidence": low_confidence,
        "reviewId": review_id
    }

@app.get("/review", response_model=List[ReviewItem])
def list_review(status: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    query = "SELECT * FROM review_queue"
    params = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    
    cursor = db.execute(query, params)
    items = []
    for row in cursor.fetchall():
        r = dict(row)
        items.append({
            "id": r['id'],
            "question": r['question'],
            "reason": r['reason'],
            "status": r['status'],
            "draftAnswer": r['draft_answer'],
            "draftCitations": json.loads(r['draft_citations_json']),
            "finalAnswer": r['final_answer'],
            "createdAt": r['created_at'],
            "resolvedAt": r['resolved_at']
        })
    return items

@app.post("/review/{id}/resolve", response_model=ResolveReviewResponse)
def resolve_review(id: str, req: ResolveReviewRequest, db: sqlite3.Connection = Depends(get_db)):
    now = int(time.time() * 1000)
    cursor = db.execute("""
        UPDATE review_queue 
        SET status = 'resolved', final_answer = ?, resolved_at = ?
        WHERE id = ?
    """, (req.finalAnswer, now, id))
    db.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review item not found")
        
    return {"ok": True, "promoteToFaq": req.promoteToFaq}

@app.get("/schedule", response_model=Optional[ScheduleConfig])
def get_schedule(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT json_blob FROM schedule_config WHERE id = 1")
    row = cursor.fetchone()
    if not row:
        return None
    return json.loads(row['json_blob'])

@app.post("/schedule", response_model=GenericOkResponse)
def set_schedule(cfg: ScheduleConfig, db: sqlite3.Connection = Depends(get_db)):
    now = int(time.time() * 1000)
    json_blob = cfg.json()
    db.execute("INSERT OR REPLACE INTO schedule_config (id, json_blob, updated_at) VALUES (1, ?, ?)", (json_blob, now))
    db.commit()
    return {"ok": True}

@app.post("/schedule/ask", response_model=ScheduleAskResponse)
def ask_schedule(req: ScheduleAskRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT json_blob FROM schedule_config WHERE id = 1")
    row = cursor.fetchone()
    if not row:
        return {"answer": "No schedule is configured yet."}
    
    s = json.loads(row['json_blob'])
    q = req.question.lower()
    
    if "holiday" in q:
        holidays = s.get('holidays', [])
        if not holidays:
            return {"answer": "No holidays configured."}
        next_holiday = holidays[0] # Simplification
        return {"answer": f"Next holiday: **{next_holiday['name']}** on **{next_holiday['date']}** ({s['timezone']})."}
        
    for day in s.get('week', []):
        if day['day'].lower() in q:
            note = f" — {day['note']}" if day.get('note') else ""
            return {"answer": f"Your **{day['day']}** schedule is **{day['start']}–{day['end']}**{note}. ({s['timezone']})"}
            
    if "oncall" in q or "on-call" in q:
        oncall = s.get('oncall', [])
        if not oncall:
            return {"answer": "No on-call schedule configured."}
        oc = oncall[0]
        note = f" — {oc['note']}" if oc.get('note') else ""
        return {"answer": f"On-call window: **{oc['from']} → {oc['to']}**{note}."}
        
    return {"answer": "I can answer schedule questions like: “What’s my schedule Monday?”, “Am I on-call this week?”, or “Any holidays coming up?”"}
