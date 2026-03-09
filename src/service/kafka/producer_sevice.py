from logging import Logger

from src.infrastructure.kafka import ProducerKafka
from src.schemas.kafka_data import EndProcessing
from src.service.config.schemas import Config


class KafkaProducerService:

    def __init__(
        self,
        producer: ProducerKafka,
        config: Config,
        logger: Logger,
    ):
        self.conf = config
        self.logger = logger
        self.producer = producer

    async def send_end_processing(self, data: EndProcessing) -> None:
        await self.producer.send_message(
            topic=self.conf.env.topic_uploading_data,
            key=self.conf.kafka_keys.new_processing,
            value=data.model_dump()
        )
