import os
from datetime import timedelta
from pathlib import Path

from pydantic import BaseModel

from src.service.config.base import init_env


class Config:
    def __init__(self):
        init_env()

        self.min_commit_count_kafka: int = 10

        self.ai_model: str = "gpt://b1g7oqla4ilph9u5f603/yandexgpt-lite/latest"

        # ограничение по запросам
        self.rpm = 15  # в минуту
        self.rpd = 500  # в день

        # Ограничение токенов (символов). Это действует на входящий и выходящий запрос
        self.tpm = 40000  # в минуту

        self.response_format = {
            "type": "json_schema",
            "json_schema": {
                "properties": {
                    "score": {"type": "integer"},
                    "verdict": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "matches": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["score", "verdict", "recommendation", "matches"],
                "type": "object"
            },
            "strict": True
        }

        self.prompt = """
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
        """

        self.env = EnvConfig.build()
        self.paths = PathsConfig.build()
        self.kafka_keys = KafkaKeys.build()
        self.lifespan_redis = LifespanInRedis.build()


class EnvConfig(BaseModel):

    yandex_cloud_api_key: str
    yandex_cloud_folder_id: str

    kafka_bootstrap_servers: str
    topic_uploading_data: str
    topic_ai_handler: str

    redis_host: str
    redis_port: int

    mode: str

    @classmethod
    def build(cls) -> "EnvConfig":
        return cls(
            yandex_cloud_api_key=os.environ['YANDEX_CLOUD_API_KEY'],
            yandex_cloud_folder_id=os.environ['YANDEX_CLOUD_FOLDER_ID'],

            kafka_bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
            topic_uploading_data=os.environ['TOPIC_UPLOADING_DATA'],
            topic_ai_handler=os.environ['TOPIC_AI_HANDLER'],

            redis_host=os.environ['REDIS_HOST'],
            redis_port=int(os.environ['REDIS_PORT']),

            mode=os.environ['MODE']
        )


class PathsConfig(BaseModel):
    base: Path
    media: Path
    log_dir: Path
    log_file: Path

    @classmethod
    def build(cls) -> "PathsConfig":
        base = Path(__file__).resolve().parents[3]
        media = base / Path("media")
        log_dir = media / "logs"
        log_file = log_dir / "ai_handler_service.log"

        media.mkdir(exist_ok=True)
        log_dir.mkdir(exist_ok=True)

        return cls(
            base=base,
            media=media,
            log_dir=log_dir,
            log_file=log_file,
        )


class KafkaKeys(BaseModel):
    new_request: str
    end_processing: str

    @classmethod
    def build(cls) -> "KafkaKeys":
        return cls(
            new_request='new_request',
            end_processing='end_processing',
        )


class LifespanInRedis(BaseModel):
    """Время жизни данных в Redis в секундах"""

    kafka_message: int

    @classmethod
    def build(cls) -> "LifespanInRedis":
        return cls(
            kafka_message=int(timedelta(hours=5).total_seconds()),
        )