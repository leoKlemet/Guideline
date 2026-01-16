from pydantic import BaseModel
from typing import List, Optional, Literal

class HealthResponse(BaseModel):
    ok: bool

AccessLevel = Literal["public", "internal", "confidential", "restricted"]

class IngestRequest(BaseModel):
    title: str
    policyKey: str
    effectiveDate: str
    access: AccessLevel
    tags: List[str]
    content: str

class IngestResponse(BaseModel):
    docId: str
    chunksCreated: int

class Chunk(BaseModel):
    id: str
    docId: str
    chunkIndex: int
    type: Literal["text", "table"]
    pageStart: int
    pageEnd: int
    content: str
    access: str
    effectiveDate: str

class Doc(BaseModel):
    id: str
    title: str
    policyKey: str
    effectiveDate: str
    access: str
    tags: List[str]
    created_at: int
    chunks: List[Chunk]

class ChatRequest(BaseModel):
    userId: str
    role: AccessLevel
    question: str

class Citation(BaseModel):
    chunkId: str
    docId: str
    docTitle: str
    pageStart: int
    pageEnd: int
    quote: str
    distance: float

class QAAnswer(BaseModel):
    answer: str
    citations: List[Citation]
    confidence: Literal["High", "Medium", "Low"]
    bestDistance: float
    lowConfidence: bool
    reviewId: Optional[str] = None

class ReviewItem(BaseModel):
    id: str
    question: str
    reason: Literal["low_confidence", "not_found", "conflict"]
    status: Literal["open", "resolved"]
    draftAnswer: Optional[str] = None
    draftCitations: List[Citation]
    finalAnswer: Optional[str] = None
    createdAt: int
    resolvedAt: Optional[int] = None

class ResolveReviewRequest(BaseModel):
    finalAnswer: str
    promoteToFaq: bool = False

class ResolveReviewResponse(BaseModel):
    ok: bool
    promoteToFaq: bool

class ScheduleConfig(BaseModel):
    timezone: str
    week: List[dict]
    oncall: Optional[List[dict]] = None
    holidays: Optional[List[dict]] = None

class ScheduleAskRequest(BaseModel):
    question: str

class ScheduleAskResponse(BaseModel):
    answer: str

class GenericOkResponse(BaseModel):
    ok: bool
