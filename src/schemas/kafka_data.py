from typing import Dict

from pydantic import BaseModel


# consumer
class NewProcessing(BaseModel):
    processing_id: int
    resume_id: int
    requirement_id: int
    user_id: int
    resume: str
    requirement: str


# producer
class EndProcessing(BaseModel):
    processing_id: int
    success: bool
    message_error: str | None
    wait_seconds: int | None
    score: int
    matches: list
    recommendation: str
    verdict: str

