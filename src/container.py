from typing import Optional

from src.infrastructure.kafka import ProducerKafka, get_producer
from src.infrastructure.redis import get_redis
from src.repository.redis.kafka_message_cache import KafkaMessageCacheRepository
from src.service.ai_handler.ai_handler import AiHandlerService
from src.service.ai_handler.limits import get_limits, LimitAiRequest
from src.service.config import get_config
from src.service.kafka.kafka_event_handler import KafkaEventHandlerService
from src.service.kafka.producer_sevice import KafkaProducerService
from src.service.utils.logger import get_logger


class Container:

    def __init__(self):

        self.config = get_config()
        self.logger = get_logger()
        self.session_redis = get_redis()
        self.producer_infra = get_producer()

        self.producer_service = KafkaProducerService(
            producer=self.producer_infra,
            config=self.config,
            logger=self.logger,
        )

        self.limit_ai_request_service = LimitAiRequest(
            limits=get_limits(),
            conf=self.config
        )
        self.ai_handler_service = AiHandlerService(
            producer=self.producer_service,
            limits=self.limit_ai_request_service,
            conf=self.config,
            logger=self.logger,
        )


        self.kafka_cache_repo = KafkaMessageCacheRepository(
            config=self.config,
            redis_session=self.session_redis
        )

        self.kafka_event_handler_service = KafkaEventHandlerService(
            ai_handler=self.ai_handler_service,
            kafka_message_cache=self.kafka_cache_repo,
            config=self.config,
            logger=self.logger,
        )


_container: Optional[Container] = None


def init_container() -> Container:
    global _container
    if _container is None:
        _container = Container()

    return _container


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    global _container
    if _container is None:
        raise RuntimeError("Service not initialized")
    return _container