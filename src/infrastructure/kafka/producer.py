import json
import socket
from logging import Logger
from aiokafka import AIOKafkaProducer

from src.service.config.schemas import Config

class ProducerKafka:

    def __init__(
        self,
        config: Config,
        logger: Logger,
    ):
        self.conf = config
        self.logger = logger

        self._bootstrap_servers = self.conf.env.kafka_bootstrap_servers
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=socket.gethostname(),
            acks="all",
            enable_idempotence=True,
            retry_backoff_ms=500,
            request_timeout_ms=30000,
            max_batch_size=16384,
            linger_ms=10,
        )

        self._started = False

    async def start(self):
        if not self._started:
            await self._producer.start()
            self._started = True
            self.logger.info("Kafka producer started")

    async def stop(self):
        if self._started:
            await self._producer.stop()
            self._started = False
            self.logger.info("Kafka producer stopped")

    async def send_message(
        self,
        topic: str,
        key: str,
        value: dict | str | bytes
    ):
        try:
            if isinstance(value, dict):
                value = json.dumps(value).encode()
            elif isinstance(value, str):
                value = value.encode()
            await self._producer.send_and_wait(
                topic=topic,
                key=key.encode(),
                value=value
            )
            self.logger.info(f"Kafka message sent to topic={topic}")

        except Exception as e:
            self.logger.exception(f"Kafka send error: {e}")

