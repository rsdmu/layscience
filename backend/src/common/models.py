from pydantic import BaseModel
from typing import List, Dict, Optional, Literal

Mode = Literal["micro", "extended"]

class StartJobRequest(BaseModel):
    mode: Mode = "micro"
    input: dict  # {doi?|url?|s3_key?}
    privacy: Literal["ephemeral","private","public"] = "ephemeral"
    language: Optional[str] = None  # target i18n

class Chunk(BaseModel):
    id: int
    page: int
    start: int
    end: int
    text: str

class EvidenceSpan(BaseModel):
    chunk_id: int
    page: int
    start: int
    end: int

class SentenceEvidence(BaseModel):
    text: str
    citations: List[int]
    spans: List[EvidenceSpan] = []

class SummaryPayload(BaseModel):
    mode: Mode
    lay_summary: str
    headline: str
    keywords: List[str]
    jargon_definitions: Dict[str, str]
    sentences: List[SentenceEvidence]
    reading_level: Dict[str, float]
    disclaimers: List[str]
    language: str = "en"

class JobStatus(BaseModel):
    id: str
    status: Literal["queued","running","done","error"]
    error: Optional[str] = None
