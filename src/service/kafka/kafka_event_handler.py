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

        # Обработчики для каждого топика
        self.handlers = {
            self.conf.kafka_topics.new_request: self._new_request,
        }

    def _get_message_uid(self, msg) -> str:
        return f"{msg.topic}:{msg.partition}:{msg.offset}"

    async def _new_request(self, data: dict):
        new_user_request = NewProcessing(**data)
        await self.ai_handler.start_processing(new_user_request)

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
            handler = self.handlers.get(msg.topic)
            if handler:
                await handler(data)
            else:
                self.logger.warning(f"Не нашли топик из config для сообщения. Топик: {msg.topic}")

            # записываем что сообщение обработано
            await self.kafka_message_cache.set(message_id)
        except Exception:
            self.logger.exception(
                f"Обработка сообщения из kafka завершилась с ошибкой. Данные о сообщении: \n"
                f"data: {data}\n"
                f"key: {key}\n"
                f"message_id: {message_id}\n\n"
                "Ошибка: "
            )
