from contextlib import asynccontextmanager

from src.container import init_container
from src.infrastructure.kafka import init_producer
from src.infrastructure.kafka.admin_client import init_admin_client, shutdown_admin_client
from src.infrastructure.kafka.consumers.run_consumers import run_consumer
from src.infrastructure.kafka.topic_manager import check_exists_topic
from src.infrastructure.redis import init_redis, close_redis
from src.service.config import init_config


@asynccontextmanager
async def start_app():
    """
    Асинхронный контекстный менеджер для запуска приложения.
    Инициализирует конфиг, Redis, Kafka, проверяет топик и запускает потребителя.
    """
    conf = init_config()
    await init_redis()
    await init_admin_client()
    await init_producer()
    init_container()
    await check_exists_topic([conf.kafka_topics.new_request, conf.kafka_topics.finished])

    consumer_runner = await run_consumer()

    try:
        # Всё готово, отдаём управление вызывающему
        yield
    finally:
        # Корректное завершение всех сервисов
        await consumer_runner.stop()
        await close_redis()
        await shutdown_admin_client()

