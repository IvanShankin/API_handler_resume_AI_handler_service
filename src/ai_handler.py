import os
import json
import openai
import tiktoken
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import error as openai_error

from src.config import GPT_MODEL, RPM, RPD, TPM, logger

load_dotenv()
OPENAI_KEY = os.getenv('OPENAI_KEY')
openai.api_key = OPENAI_KEY # загрузка ключа

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

async def run_ai_handler(requirements: str, resume: str)-> dict:
    """
    :param requirements:
    :param resume:
    :return: dict{
        "success": bool,
        "response": dict{
            'score': int, # X/100 совместимость с требованиями
            'matches': list, # перечисление навыков
            'recommendation': str, # рекомендации по найму
            'verdict': str, # заключение "Подходит" или "Не подходит"
        },
        "message_error": str, # опционально, если 'success' == False
        "wait_seconds": int, # опционально, если есть rate limit
    }
    """
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

Выводи результат СТРОГО В ФОРМАТЕ JSON, без пояснений, без лишнего текста. Пример:

{
  "score": 35,
  "matches": ["Python", "SQL", "опыт с ИИ"],
  "recommendation": "Кандидат имеет частичные совпадения, но отсутствует профильный опыт. Рассматривать не рекомендуется.",
  "verdict": "Не подходит"
}

---

""" + f'Требования к вакансии: {requirements} \nКандидат:{resume}'

    limit = await check_limits(prompt)

    if not limit['result']: # если превышен лимит
        return {
            "success": False,
            "response": None,
            "message_error": limit['message'],
            "wait_seconds": limit['wait_seconds'],
        }

    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0  # строгий, стабильный ответ
        )
    except openai_error.PermissionError:
        logger.error('Сервер не должен отправлять запросы к GPT с Российского IP!')
        return {
            "success": False,
            "response": None,
            "message_error": 'Сервер не должен отправлять запросы к GPT с Российского IP!',
            "wait_seconds": None,
        }
    except openai_error.RateLimitError as e:
        logger.warning('Получили rate limit как ошибку!') # логируем т.к. сюда не должны попадать
        return {
            "success": False,
            "response": None,
            "message_error": 'Пожалуйста подождите 20 секунд',
            "wait_seconds": 20, # в ошибке всегда просят подождать 20 секунд
        }
    except Exception as e:
        logger.error(f'Неожиданная ошибка при запросе к OpenAI: {str(e)}')  # логируем
        return {
            "success": False,
            "response": None,
            "message_error": 'Произошла внутренняя ошибка',
            "wait_seconds": None,
        }

    current_tokens_minute += len(response['choices'][0]['message']['content'])

    # очищаем ответ от маркеров ```json
    cleaned_response = response['choices'][0]['message']['content'].replace('```json', '').replace('```', '').strip()

    response_json = json.loads(cleaned_response)

    return {
        "success": True,
        "response": response_json,
        "message_error": None,
        "wait_seconds": None,
    }