import asyncio
from typing import Optional

from src.container import get_container
from src.infrastructure.kafka.consumers.consumer import ConsumerKafka
from src.service.utils.logger import get_logger


class ConsumerRunner:
    def __init__(self, consumer: ConsumerKafka):
        self.consumer = consumer
        self.logger = get_logger()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        for _ in range(5):
            try:
                self._task = asyncio.create_task(
                    self.consumer.run_consumer()
                )
                break
            except Exception as e:
                self.logger.warning(f"Cannot start consumer, retrying: {e}")
                await asyncio.sleep(2)

    async def stop(self):
        if not self._task:
            return

        # даём сигнал остановки
        await self.consumer.stop()

        # ждём корректного завершения
        await self._task


async def run_consumer() -> ConsumerRunner:
    container = get_container()

    consumer = ConsumerKafka(
        topics=[container.config.kafka_topics.new_request],
        handler_msg_cls=container.kafka_event_handler_service,
        logger=container.logger,
        config=container.config
    )

    runner = ConsumerRunner(consumer)
    await runner.start()

    return runner