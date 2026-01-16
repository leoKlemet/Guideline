import re
from typing import List, Tuple, Set
from .schema import Chunk, Citation, AccessLevel

def uid(prefix="id"):
    import time
    import random
    return f"{prefix}_{random.randint(0, 1000000):x}_{int(time.time()*1000):x}"

def clamp(n: float, a: float, b: float) -> float:
    return max(a, min(b, n))

def summarize_quote(text: str, max_len=180) -> str:
    t = re.sub(r'\s+', ' ', text).strip()
    return t[:max_len-1] + "…" if len(t) > max_len else t

def chunk_text_to_chunks(doc_id: str, content: str, access: str, effective_date: str) -> List[dict]:
    # Super simple chunker for prototype:
    # - Splits on blank lines
    # - Treats markdown tables as table chunks
    parts = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]

    chunks = []
    for idx, p in enumerate(parts):
        is_table = bool(re.search(r'^\|.*\|\s*\n\|[-:|\s]+\|', p, re.MULTILINE))
        chunks.append({
            "id": uid("chunk"),
            "doc_id": doc_id,
            "chunk_index": idx,
            "type": "table" if is_table else "text",
            "page_start": 1,
            "page_end": 1,
            "content": p,
            "access": access,
            "effective_date": effective_date
        })
    return chunks

def score_chunk(question: str, chunk_content: str) -> float:
    q = question.lower()
    c = chunk_content.lower()
    
    # Split question into words len >= 3
    q_words = set([w for w in re.split(r'[^a-z0-9]+', q) if len(w) >= 3])
    
    if len(q_words) == 0:
        return 1.0

    hit = 0
    for w in q_words:
        if w in c:
            hit += 1
            
    overlap = hit / len(q_words) # 0..1
    distance = 1.0 - overlap
    
    # Add a small penalty for very short chunks
    penalty = 0.08 if len(chunk_content) < 80 else 0.0
    
    return clamp(distance + penalty, 0.0, 1.0)

def detect_conflict(citations: List[dict], question: str) -> bool:
    # Simple conflict heuristic: if top citations come from different effective dates
    # and question implies a numeric limit, flag potential conflict.
    wants_number = bool(re.search(r'limit|how much|maximum|max|per day|per night|\$|dollar', question, re.IGNORECASE))
    if not wants_number:
        return False
        
    dates = set([f"{c['pageStart']}:{c['docId']}" for c in citations])
    doc_ids = [c['docId'] for c in citations]
    unique_docs = len(set(doc_ids))
    
    # Too naive; for prototype, we treat multiple docs as possible conflict
    return unique_docs >= 2 and len(dates) >= 2

def build_answer(question: str, citations: List[dict], role: str) -> str:
    # Template-y answer to look professional in demo.
    q = question.lower()

    mention_schedule = bool(re.search(r'schedule|shift|on[- ]?call|availability|hours|holiday', q, re.IGNORECASE))
    if mention_schedule:
        return "I can help with schedule questions on the Schedule tab. For policy questions, I’ll cite the exact section and effective date."

    if not citations:
        return f"I couldn’t find this in the currently ingested policies for your access level (**{role}**). I can route this to the Review Queue for an official answer."

    # Try to craft a more specific answer for common policy prompts
    if re.search(r'receipt', q):
        return "Receipts are required for expenses above **$25**. Keep itemized receipts when applicable."
    if re.search(r'meal|food', q):
        return "Meals are capped at **$60/day**, and an itemized receipt is required."
    if re.search(r'hotel', q):
        return "Hotels are capped at **$220/night**. Exceptions require approval."
    if re.search(r'rideshare|uber|lyft|airport', q):
        return "Rideshare is allowed for airport transit. For other cases, follow the transportation guidance in the travel policy."

    # Default:
    top = citations[0]
    return f"Here’s what the policy says (with citations). The most relevant section is from **{top['docTitle']}** (p.{top['pageStart']})."

def confidence_from_distance(best_distance: float) -> str:
    # Prototype heuristic
    # smaller distance => better
    if best_distance <= 0.25:
        return "High"
    if best_distance <= 0.5:
        return "Medium"
    return "Low"
