from typing import Dict

from pydantic import BaseModel


class AiResponse(BaseModel):
    success: bool
    response: Dict = {}
    message_error: str | None
    wait_seconds: int | None

