from logging import Logger

from orjson import orjson

from src.repository.redis.kafka_message_cache import KafkaMessageCacheRepository
from src.schemas.kafka_data import NewProcessing
from src.service.ai_handler.ai_handler import AiHandlerService
from src.service.config.schemas import Config


class KafkaEventHandlerService:

    def __init__(
        self,
        ai_handler: AiHandlerService,
        kafka_message_cache: KafkaMessageCacheRepository,
        logger: Logger,
        config: Config
    ):
        self.ai_handler = ai_handler
        self.kafka_message_cache = kafka_message_cache
        self.logger = logger
        self.conf = config

    def _get_message_uid(self, msg) -> str:
        return f"{msg.topic}:{msg.partition}:{msg.offset}"

    async def _handler_by_key(self, data: dict, key: str, message_id: str):

        if key == self.conf.kafka_keys.new_request:
            new_user_request = NewProcessing(**data)
            await self.ai_handler.start_processing(new_user_request)

        # записываем что сообщение обработано
        await self.kafka_message_cache.set(message_id)

    async def handler_messages(self, msg):
        """
        :return: Успех обработки. Если уже было обработанно ранее, то вернёт False
        """
        message_id = self._get_message_uid(msg)

        if await self.kafka_message_cache.get(message_id):
            return

        data = orjson.loads(msg.value.decode("utf-8"))
        key = (
            msg.key.decode("utf-8")
            if msg.key
            else None
        )

        try:
            await self._handler_by_key(data, key, message_id)
        except Exception:
            self.logger.exception(
                f"Обработка сообщения из kafka завершилась с ошибкой. Данные о сообщении: \n"
                f"data: {data}\n"
                f"key: {key}\n"
                f"message_id: {message_id}\n\n"
                "Ошибка: "
            )
