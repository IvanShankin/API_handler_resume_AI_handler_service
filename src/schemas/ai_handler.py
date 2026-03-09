from typing import List, Optional
from openai import BaseModel


class AIResponse(BaseModel):
    score: int
    verdict: str
    recommendation: str
    matches: List[str]


class AIHandlerResult(BaseModel):
    success: bool
    response: Optional[AIResponse]
    message_error: Optional[str]
    wait_seconds: Optional[int]


