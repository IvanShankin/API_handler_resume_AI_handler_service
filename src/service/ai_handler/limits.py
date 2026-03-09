from datetime import datetime, timedelta

import tiktoken

from src.schemas.ai_limits import Limits, LimitChecks
from src.service.config.schemas import Config

_request_counter_minute = 0
_request_counter_day = 0
_last_reset_minute = datetime.now()
_last_reset_day = datetime.now()
_current_tokens_minute = 0


def get_limits():
    global _request_counter_minute
    global _request_counter_day
    global _last_reset_minute
    global _last_reset_day
    global _current_tokens_minute

    return Limits(
        request_counter_minute=_request_counter_minute,
        request_counter_day=_request_counter_day,
        last_reset_minute=_last_reset_minute,
        last_reset_day=_last_reset_day,
        current_tokens_minute=_current_tokens_minute,
    )


class LimitAiRequest:

    def __init__(self, limits: Limits, conf: Config):
        self.limits = limits
        self.conf = conf

    def count_tokens(self, text: str) -> int:
        """Вернёт количество токенов в тексте"""
        enc = tiktoken.encoding_for_model('gpt-4')
        return len(enc.encode(text))

    def get_waiting_time(self, last_reset: datetime) -> int:
        """Вернёт время ожидания в секундах до следующей минуты"""
        now = datetime.now()
        elapsed = now - last_reset
        return max(0, 60 - elapsed.seconds)

    def get_daily_waiting_time(self) -> int:
        """Вернёт время ожидания в секундах до конца дня"""
        now = datetime.now()
        end_of_day = datetime(now.year, now.month, now.day) + timedelta(days=1)
        return int((end_of_day - now).total_seconds())

    def add_token_minutes(self, how_much_add: int):
        """:param how_much_add: Количество токенов которое необходимо добавить"""
        self.limits.current_tokens_minute += how_much_add

    async def check_limits(self, prompt: str) -> LimitChecks:
        """Проверяет, не превышены ли лимиты RPM, RPD и TPM"""
        prompt_tokens = self.count_tokens(prompt)

        # Сброс счетчика RPM каждую минуту
        if datetime.now().minute - self.limits.last_reset_minute.minute > 60:
            self.limits.request_counter_minute = 0
            self.limits.current_tokens_minute = 0
            self.limits.last_reset_minute = datetime.now()

        # Сброс счетчика RPD каждый день
        if datetime.now().date() != self.limits.last_reset_day.date():
            self.limits.request_counter_day = 0
            self.limits.last_reset_day = datetime.now()

        # Проверка RPM
        if self.limits.request_counter_minute >= self.conf.rpm:
            waiting_seconds = self.get_waiting_time(self.limits.last_reset_minute)
            return LimitChecks(
                result=False,
                message=f'Пожалуйста подождите {waiting_seconds} секунд',
                wait_seconds=waiting_seconds,
                prompt_tokens=prompt_tokens
            )

        # Проверка RPD
        if self.limits.request_counter_day >= self.conf.rpd:
            waiting_seconds = self.get_daily_waiting_time()
            return LimitChecks(
                result=False,
                message=f'Превышен лимит запросов в день ({self.conf.rpd}). Попробуйте завтра.',
                wait_seconds=waiting_seconds,
                prompt_tokens=prompt_tokens
            )

        # Проверка TPM
        if self.limits.current_tokens_minute + prompt_tokens > self.conf.tpm:
            waiting_seconds = self.get_waiting_time(self.limits.last_reset_minute)
            return LimitChecks(
                result=False,
                message=f'Пожалуйста подождите {waiting_seconds} секунд',
                wait_seconds=waiting_seconds,
                prompt_tokens=prompt_tokens
            )

        # Обновление счетчиков
        self.limits.request_counter_minute += 1
        self.limits.request_counter_day += 1
        self.limits.current_tokens_minute += prompt_tokens

        return LimitChecks(
            result=True,
            message=f'no restrictions',
            wait_seconds=0,
            prompt_tokens=prompt_tokens
        )