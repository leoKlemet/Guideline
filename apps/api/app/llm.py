import os
import json
import httpx
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class LLMResult(BaseModel):
    answer: str
    confidence: str  # "High", "Medium", "Low"
    escalate: bool
    used_chunk_ids: List[str]
    reason: Optional[str] = None

async def compose_answer(
    question: str, 
    role: str, 
    candidates: List[Dict[str, Any]], 
    best_distance: float
) -> LLMResult:
    """
    Composes an answer using the configured LLM provider.
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    
    if provider == "mock":
        return _mock_chat(question, candidates, best_distance)
    elif provider in ["openai", "openai_compat", "lm_studio"]:
        return await _openai_chat(question, candidates)
    else:
        # Fallback to mock if unknown
        return _mock_chat(question, candidates, best_distance)

def _mock_chat(question: str, candidates: List[Dict], best_distance: float) -> LLMResult:
    """
    Deterministic mock provider for testing.
    """
    if not candidates:
        return LLMResult(
            answer="I couldn't find any information about that in the policy.",
            confidence="Low",
            escalate=False, 
            used_chunk_ids=[]
        )
        
    # Simple logic for mock
    top_candidate = candidates[0]
    
    # Simulate confidence based on distance
    confidence = "High"
    if best_distance > 0.4:
        confidence = "Medium"
    if best_distance > 0.6:
        confidence = "Low"
        
    return LLMResult(
        answer=f"Mock Answer: Based on {top_candidate.get('docTitle', 'doc')}, feature is available.",
        confidence=confidence,
        escalate=False,
        used_chunk_ids=[c.get('chunkId') for c in candidates[:2]] # Cite top 2
    )

async def _openai_chat(question: str, candidates: List[Dict]) -> LLMResult:
    """
    Calls OpenAI-compatible endpoint (e.g., LM Studio, Ollama via /v1, or real OpenAI).
    """
    base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    model = os.getenv("LLM_MODEL", "model-identifier")
    
    # 1. Build Context
    context_text = ""
    for c in candidates:
        context_text += f"---\nDoc: {c.get('docTitle', 'Unknown')}\nPage: {c.get('pageStart', '?')}\nContent: {c.get('quote', '')}\n"

    # 2. Construct Prompt (Force JSON)
    system_prompt = (
        "You are a helpful internal policy assistant.\n"
        "Use ONLY the provided Context to answer the User Question.\n"
        "If sources are insufficient or conflicting, set escalate=true.\n"
        "Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  "answer": "string",\n'
        '  "confidence": "High|Medium|Low",\n'
        '  "escalate": boolean,\n'
        '  "used_chunk_ids": ["string"],\n'
        '  "reason": "optional string"\n'
        "}"
    )
    
    user_message = f"Context:\n{context_text}\n\nUser Question: {question}"
    
    # 3. Call Endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Note: headers often require Authorization
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            resp = await client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.0,
                    # "response_format": {"type": "json_object"} # Not all local servers support this logic yet, relying on prompt
                },
                headers=headers
            )
            resp.raise_for_status()
            result = resp.json()
            
            # Parse content
            content_str = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Cleaning markdown code blocks if present
            if "```json" in content_str:
                content_str = content_str.split("```json")[1].split("```")[0].strip()
            elif "```" in content_str:
                content_str = content_str.split("```")[1].strip()
                
            try:
                structured = json.loads(content_str)
            except json.JSONDecodeError:
                # Fallback if model returns text
                print(f"LLM JSON Parse Error. Raw: {content_str}")
                return LLMResult(
                    answer=content_str[:500] + "...", 
                    confidence="Low", 
                    escalate=True, 
                    used_chunk_ids=[], 
                    reason="Invalid JSON response"
                )
            
            return LLMResult(
                answer=structured.get("answer", "Error parsing answer"),
                confidence=structured.get("confidence", "Low"),
                escalate=structured.get("escalate", False),
                used_chunk_ids=structured.get("used_chunk_ids", []),
                reason=structured.get("reason")
            )
            
    except Exception as e:
        print(f"LLM Error: {e}")
        return LLMResult(
            answer="I encountered an issue connecting to the AI helper.",
            confidence="Low",
            escalate=True,
            used_chunk_ids=[],
            reason=str(e)
        )
