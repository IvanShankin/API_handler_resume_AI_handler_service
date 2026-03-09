import json
from typing import Optional, List
from unittest.mock import Mock

from orjson import orjson
from schemas import ProducerMessage

from src.infrastructure.kafka import ProducerKafka
from src.service.config import get_config
from src.service.utils.logger import get_logger


class FakeAdminClient:
    def __init__(self):
        pass

    async def list_topics(self):
        conf = get_config()
        return [conf.env.topic_uploading_data]


class KafkaTestProducer(ProducerKafka):
    """
    Async helper для тестов.
    """
    def __init__(self,):
        super().__init__(
            config=get_config(),
            logger=get_logger()
        )
        self.all_message: List[ProducerMessage] = []

    async def send_message(
        self,
        topic: str,
        key: str,
        value: dict | str | bytes
    ):
        """Сохранит все """
        self.all_message.append(
            ProducerMessage(topic=topic, key=key, value=value)
        )

    async def start(self):
        pass

    async def stop(self):
        pass


class FakeKafkaMessage:
    def __init__(
        self,
        data: dict,
        topic: str = "test_topic",
        key: Optional[str] = None,
        partition: int = 0,
        offset: int = 0,
    ) -> None:
        self.topic: str = topic
        self.partition: int = partition
        self.offset: int = offset

        self.key: Optional[bytes] = (
            key.encode("utf-8") if key is not None else None
        )

        self.value: bytes = orjson.dumps(data)



class FakeAiClient:

    def __init__(
        self,
        score: int = 35,
        matches: List[str] | None = None,
        recommendation: str = "Кандидат имеет частичные совпадения, но отсутствует профильный опыт. Рассматривать не рекомендуется.",
        verdict: str = "Не подходит",
    ):
        if matches is None:
            matches = ["Python", "SQL", "опыт с ИИ"]

        response_dict = {
            "score": score,
            "matches": matches,
            "recommendation": recommendation,
            "verdict": verdict,
        }

        response_json = json.dumps(response_dict)

        class FakeResponse:
            def __init__(self, text: str):
                self.output_text = text

        class FakeResponses:
            def __init__(self, text: str):
                self.text = text

            async def create(self, **kwargs):
                return FakeResponse(self.text)

        self.responses = FakeResponses(response_json)
