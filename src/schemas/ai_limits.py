from datetime import datetime

from pydantic import BaseModel


class Limits(BaseModel):
    request_counter_minute: int    # счётчик запросов в минуту
    request_counter_day: int       # счётчик запросов в день
    last_reset_minute: datetime    # время последнего обновления счётчика по минутам
    last_reset_day: datetime       # время последнего обновления счётчика по дням
    current_tokens_minute: int     # количество токенов использованных за последнюю минуту


class LimitChecks(BaseModel):
    result: bool        # True если можно выполнить запрос, False если лимит превышен
    message: str        # причина блокировки или 'no restrictions'
    wait_seconds: int   # сколько секунд ждать до сброса лимита
    prompt_tokens: int  # сколько токенов содержится в запросе