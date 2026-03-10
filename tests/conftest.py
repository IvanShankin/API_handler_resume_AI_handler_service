import pytest_asyncio
import fakeredis

from typing import List

from src.container import init_container, get_container
from src.infrastructure.kafka import set_producer, init_producer
from src.infrastructure.kafka.admin_client import set_admin_client
from src.infrastructure.kafka.topic_manager import check_exists_topic
from src.infrastructure.redis import set_redis, get_redis
from src.service.config import init_config

from tests.helper_func import KafkaTestProducer, FakeAdminClient, FakeAiClient


@pytest_asyncio.fixture(scope='session', autouse=True)
async def start_test():
    conf = init_config()
    if conf.env.mode != "TEST":
        raise Exception("Используется не тестовый режим!")

    await set_redis(fakeredis.aioredis.FakeRedis())
    set_admin_client(FakeAdminClient())

    await set_producer(KafkaTestProducer())
    init_container()
    await check_exists_topic([conf.kafka_topics.new_request, conf.kafka_topics.finished])


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clearing_redis():
    redis = get_redis()
    await redis.flushall()
    await redis.aclose()
    return redis


@pytest_asyncio.fixture(scope="function", autouse=True)
async def replace_producer() -> KafkaTestProducer:
    fake_producer = KafkaTestProducer()
    container = get_container()
    container.producer_service.producer = fake_producer
    return await set_producer(fake_producer)


@pytest_asyncio.fixture(scope="function")
async def replace_ai_model():
    def _fabric(
        score: int = 35,
        matches: List[str] = ["Python", "SQL", "опыт с ИИ"],
        recommendation: str = "Кандидат имеет частичные совпадения, но отсутствует профильный опыт. Рассматривать не рекомендуется.",
        verdict: str = "Не подходит",
    ) -> None:
        container = get_container()
        container.ai_handler_service.client = FakeAiClient(
            score=score,
            matches=matches,
            recommendation=recommendation,
            verdict=verdict,

        )

    return _fabric