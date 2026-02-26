import os
import json
from openai import AsyncOpenAI
import tiktoken
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import PermissionDeniedError, RateLimitError

from src.config import GPT_MODEL, RPM, RPD, TPM, logger, RESPONSE_FORMAT
from src.models import AiResponse

load_dotenv()
YANDEX_CLOUD_API_KEY = os.getenv('YANDEX_CLOUD_API_KEY')
YANDEX_CLOUD_FOLDER_ID = os.getenv('YANDEX_CLOUD_FOLDER_ID')

client = AsyncOpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER_ID,
)


# Глобальные счетчики и временные метки
request_counter_minute = 0 # счётчик запросов в минуту
request_counter_day = 0 # счётчик запросов в день
last_reset_minute = datetime.now() # время последнего обновления счётчика по минутам
last_reset_day = datetime.now() # время последнего обновления счётчика по дням
current_tokens_minute = 0 # количество токенов использованных за последнюю минуту

def count_tokens(text: str)->int:
    """Вернёт количество токенов в тексте"""
    enc = tiktoken.encoding_for_model('gpt-4')
    return len(enc.encode(text))

def get_waiting_time(last_reset: datetime) -> int:
    """Вернёт время ожидания в секундах до следующей минуты"""
    now = datetime.now()
    elapsed = now - last_reset
    return max(0, 60 - elapsed.seconds)

def get_daily_waiting_time(last_reset: datetime) -> int:
    """Вернёт время ожидания в секундах до конца дня"""
    now = datetime.now()
    end_of_day = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return int((end_of_day - now).total_seconds())

async def check_limits(prompt: str) -> dict:
    """Проверяет, не превышены ли лимиты RPM, RPD и TPM.
    :returns dict{
        'result': bool,  # True если можно выполнить запрос, False если лимит превышен
        'message': str,  # причина блокировки или 'no restrictions'
        'wait_seconds': int  # сколько секунд ждать до сброса лимита
    }
    """
    global request_counter_minute, request_counter_day, last_reset_minute, last_reset_day, current_tokens_minute

    # Сброс счетчика RPM каждую минуту
    if datetime.now().minute - last_reset_minute.minute > 60:
        request_counter_minute = 0
        current_tokens_minute = 0
        last_reset_minute = datetime.now()

    # Сброс счетчика RPD каждый день
    if datetime.now().date() != last_reset_day.date():
        request_counter_day = 0
        last_reset_day = datetime.now().date()

    # Проверка RPM
    if request_counter_minute >= RPM:
        waiting_seconds = get_waiting_time(last_reset_minute)
        return {
            'result': False,
            'message': f'Пожалуйста подождите {waiting_seconds} секунд',
            'wait_seconds': waiting_seconds
        }

    # Проверка RPD
    if request_counter_day >= RPD:
        waiting_seconds = get_daily_waiting_time(last_reset_day)
        return {
            'result': False,
            'message': f'Превышен лимит запросов в день ({RPD}). Попробуйте завтра.',
            'wait_seconds': waiting_seconds
        }

    # Проверка TPM
    prompt_tokens = count_tokens(prompt)
    if current_tokens_minute + prompt_tokens > TPM:
        waiting_seconds = get_waiting_time(last_reset_minute)
        return {
            'result': False,
            'message': f'Пожалуйста подождите {waiting_seconds} секунд',
            'wait_seconds': waiting_seconds
        }

    # Обновление счетчиков
    request_counter_minute += 1
    request_counter_day += 1
    current_tokens_minute += prompt_tokens

    return {'result': True, 'message': 'no restrictions', 'wait_seconds': 0 }

async def run_ai_handler(requirements: str, resume: str) -> AiResponse:
    global current_tokens_minute
    prompt = """
Ты — AI-рекрутер. Твоя задача — строго и объективно оценить соответствие кандидата требованиям вакансии.

Важно:
- Не выдумывай. Если в резюме явно НЕ указан навык или опыт — считай, что его НЕТ.
- Никаких позитивных предположений.
- Не перечисляй навыки, которые НЕ совпадают с требованиями вакансии.
- Не используй формулировки вроде: "может подойти", "возможно", "при дополнительном обучении".

Выполни строго следующие шаги:
1. Определи 5–7 ключевых требований из вакансии.
2. Проверь, какие из них совпадают с профилем кандидата (только точные или явные совпадения).
3. Подсчитай процент совпадений и выдай объективную оценку от 0 до 100.
4. Если совпадает менее 3 требований — оценка не выше 40. Если 0–1 — 0–20.
5. Сформулируй краткую рекомендацию по найму (1–2 предложения).
6. Дай финальный вердикт: "Подходит" или "Не подходит".

Выводи результат СТРОГО В ФОРМАТЕ JSON, без пояснений, без лишнего текста. 

Формат:
{
  "score": <число>,
  "verdict": <строка>,
  "recommendation": <строка>,
  "matches": [<список строк>]
}

Пример:

{
  "score": 35,
  "matches": ["Python", "SQL", "опыт с ИИ"],
  "recommendation": "Кандидат имеет частичные совпадения, но отсутствует профильный опыт. Рассматривать не рекомендуется.",
  "verdict": "Не подходит"
}

---

""" + f"Требования к вакансии: {requirements} \nКандидат:{resume}"

    limit = await check_limits(prompt)
    if not limit['result']: # если привышен лимит
        return AiResponse(
            success=False,
            message_error=limit['message'],
            wait_seconds=limit['wait_seconds'],
        )

    try:
        logger.info("Начата обработка запроса")
        # Новый современный метод
        response = await client.responses.create(
            model=GPT_MODEL,
            input=prompt,
            temperature=0
        )
        logger.info("Обработка завершена без ошибок")
    except PermissionDeniedError:
        logger.exception('Сервер не должен отправлять запросы к GPT с Российского IP!')
        return AiResponse(
            success=False,
            message_error='Сервер не должен отправлять запросы к GPT с Российского IP!',
            wait_seconds=None,
        )
    except RateLimitError as e:
        logger.error(f'Получили rate limit как ошибку!. {str(e)}')
        return AiResponse(
            success=False,
            message_error='Пожалуйста подождите 20 секунд',
            wait_seconds=None,
        )
    except Exception as e:
        logger.exception(f'Неожиданная ошибка при запросе к OpenAI: {str(e)}')
        return AiResponse(
            success=False,
            message_error='Произошла внутренняя ошибка',
            wait_seconds=None,
        )

    content = response.output_text
    logger.info(f"response AI: {content}")
    current_tokens_minute += len(content)

    cleaned_response = content.replace('```json', '').replace('```', '').strip()
    response_json = json.loads(cleaned_response)

    return AiResponse(
        success=True,
        response=response_json,
        message_error=None,
        wait_seconds=None,
    )