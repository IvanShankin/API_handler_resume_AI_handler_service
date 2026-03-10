import pytest

from src.container import get_container
from src.schemas.kafka_data import NewProcessing, EndProcessing
from tests.helper_func import FakeKafkaMessage


@pytest.mark.asyncio
async def test_new_processing(replace_producer, replace_ai_model, monkeypatch):
    replace_ai_model()

    container = get_container()
    kafka_handler = container.kafka_event_handler_service

    await kafka_handler.handler_messages(FakeKafkaMessage(
        data=NewProcessing(
            processing_id=1,
            resume_id=1,
            requirement_id=1,
            user_id=1,
            resume="Тестовое резюме",
            requirement="Тестовые требования"
        ).model_dump(),
        topic=container.config.kafka_topics.new_request,
    ))

    assert replace_producer.all_message
    data_kafka = EndProcessing.model_validate(replace_producer.all_message[0].value)

    assert data_kafka.processing_id == 1
    assert data_kafka.score == 35



