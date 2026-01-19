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

import google.generativeai as genai
import os

# Configure in main.py, but we can helper here
def get_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("WARN: No GEMINI_API_KEY found. AI answers will fail.")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-flash-latest')

def build_answer(question: str, citations: List[dict], role: str) -> str:
    q = question.lower()
    
    # Still keep the schedule override for now as that's a different "skill"
    mention_schedule = bool(re.search(r'schedule|shift|on[- ]?call|availability|hours|holiday', q, re.IGNORECASE))
    if mention_schedule:
        return "I can help with schedule questions on the Schedule tab. For policy questions, I’ll cite the exact section and effective date."

    if not citations:
        return f"I couldn’t find this in the currently ingested policies for your access level (**{role}**). I can route this to the Review Queue for an official answer."

    # REAL LLM GENERATION
    model = get_model()
    if not model:
        return "System configuration error: GEMINI_API_KEY is missing. Please set it in .env to enable AI generation."

    # Construct Context
    context_text = ""
    print(f"DEBUG: Generating answer for '{question}' with {len(citations)} citations.")
    for c in citations:
        txt = c.get('quote', '')
        print(f"DEBUG: Citation: {c.get('docTitle')} - {txt[:50]}...")
        context_text += f"---\nDocument: {c.get('docTitle', 'Unknown')}\nPage: {c.get('pageStart')}\nContent: {txt}\n"

    prompt = f"""You are a helpful internal policy assistant for a company. 
    Answer the user's question based ONLY on the following context (citations from policy documents).
    
    Rule 1: If the answer is not in the context, say "I don't have enough information in the provided policies to answer this."
    Rule 2: Cite the source (Document title or page) naturally if relevant, but the UI already shows citations, so focus on the answer text.
    Rule 3: Be concise and professional.
    Rule 4: Do not include "In the context..." or "According to the documents..." prefixes excessively. just answer directly.
    
    Context:
    {context_text}
    
    User Question: {question}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I encountered an error generating the answer: {str(e)}"

def confidence_from_distance(best_distance: float) -> str:
    # Prototype heuristic
    # smaller distance => better
    if best_distance <= 0.35: # Adjusted slightly for semantics
        return "High"
    if best_distance <= 0.6:
        return "Medium"
    return "Low"
