import asyncio
import json
import pytest

from confluent_kafka import KafkaError

from src.config import KEY_NEW_NOTIFICATIONS, KEY_NEW_PROCESSING, KEY_NEW_REQUEST
from src.dependencies.kafka_dependencies import producer
from src.dependencies.redis_dependencies import RedisWrapper
from tests.conftest import (
    consumer, KAFKA_TOPIC_FOR_UPLOADING_DATA, KAFKA_TOPIC_FOR_AI_HANDLER,
    KAFKA_TOPIC_FOR_NOTIFICATIONS, RESUME_BY_20_POINT,
    RESUME_BY_60_POINT,  RESUME_BY_100_POINT, REQUIREMENTS
)



@pytest.mark.asyncio
@pytest.mark.parametrize(
    'processing_id, resume, min_score, max_score',
    [
        (1, RESUME_BY_20_POINT, 0, 40),
        (2, RESUME_BY_60_POINT, 40, 80),
        (3, RESUME_BY_100_POINT, 80, 100),
    ]

)
async def test_success(processing_id, resume, min_score, max_score, clearing_kafka):
    async with RedisWrapper() as redis: # очистка redis
        await redis.flushdb()

    producer.sent_message(
        topic=KAFKA_TOPIC_FOR_AI_HANDLER,
        key=KEY_NEW_REQUEST,
        value={
            'callback_url': 'https://test_url/',
            'processing_id': processing_id,
            'user_id': 2,
            'resume_id': 3,
            'requirements_id': 4,
            'requirements': REQUIREMENTS,
            'resume': resume
        }
    )

    consumer.subscribe([KAFKA_TOPIC_FOR_NOTIFICATIONS, KAFKA_TOPIC_FOR_UPLOADING_DATA])

    await asyncio.sleep(5) # даём время на обработку

    # Данные с Kafka
    data_kafka_new_sending = None
    data_kafka_new_processing = None
    for i in range(40):
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                if i == 39:
                    raise Exception("Не удалось получить сообщение от Kafka!")
                continue
            if msg.key().decode('utf-8') == KEY_NEW_NOTIFICATIONS:
                data_kafka_new_sending = json.loads(msg.value().decode('utf-8'))
            elif msg.key().decode('utf-8') == KEY_NEW_PROCESSING:
                data_kafka_new_processing = json.loads(msg.value().decode('utf-8'))
            else:
                raise Exception(f"Ожидался ключ {KEY_NEW_PROCESSING} или {KEY_NEW_NOTIFICATIONS}, получен {msg.key().decode('utf-8')}")

            # Если оба сообщения получены, выходим из цикла
            if data_kafka_new_sending and data_kafka_new_processing:
                break
        except KafkaError as e:
            raise Exception(f"Ошибка Kafka: {e}")

    async with RedisWrapper() as redis:
        result_redis = await redis.get(f'processed_messages:{processing_id}')
        assert result_redis

    # Проверка данных в Kafka
    # Проверяем сообщение из топика KAFKA_TOPIC_FOR_NOTIFICATIONS
    assert data_kafka_new_sending is not None, "Не получено сообщение из топика KAFKA_TOPIC_FOR_NOTIFICATIONS"
    assert data_kafka_new_sending['success'] is True, "Обработка AI завершилась с ошибкой"
    assert isinstance(data_kafka_new_sending['response'], dict), "Ответ AI должен быть словарем"

    assert min_score <= data_kafka_new_sending['response']['score'] <= max_score  # проверка на соответствие баллов

    response = data_kafka_new_sending['response']
    assert response['callback_url'] == 'https://test_url/', "Неверный callback_url" # В данных для бд его не надо сравнивать
    assert response['processing_id'] == processing_id, "Неверный processing_id"
    assert response['user_id'] == 2, "Неверный user_id"
    assert response['resume_id'] == 3, "Неверный resume_id"
    assert response['requirements_id'] == 4, "Неверный requirements_id"
    assert isinstance(response['score'], int), "Score должен быть целым числом"
    assert min_score <= response['score'] <= max_score, f"Score должен быть в диапазоне {min_score}-{max_score}"
    assert isinstance(response['matches'], list), "Matches должен быть списком"
    assert isinstance(response['recommendation'], str), "Recommendation должен быть строкой"
    assert response['verdict'] in ["Подходит", "Не подходит"], "Verdict должен быть 'Подходит' или 'Не подходит'"

    # Проверяем сообщение из топика KAFKA_TOPIC_FOR_UPLOADING_DATA (должно быть только при успешной обработке)
    assert data_kafka_new_processing is not None, "Не получено сообщение из топика KAFKA_TOPIC_FOR_UPLOADING_DATA"
    assert data_kafka_new_processing['processing_id'] == processing_id, "Неверный processing_id в KAFKA_TOPIC_FOR_UPLOADING_DATA"
    assert data_kafka_new_processing['user_id'] == 2, "Неверный user_id в KAFKA_TOPIC_FOR_UPLOADING_DATA"
    assert data_kafka_new_processing['resume_id'] == 3, "Неверный resume_id в KAFKA_TOPIC_FOR_UPLOADING_DATA"
    assert data_kafka_new_processing['requirements_id'] == 4, "Неверный requirements_id в KAFKA_TOPIC_FOR_UPLOADING_DATA"
    assert data_kafka_new_processing['score'] == response['score'], "Score в KAFKA_TOPIC_FOR_UPLOADING_DATA должен совпадать с sending"
    assert data_kafka_new_processing['matches'] == response['matches'], "Matches в KAFKA_TOPIC_FOR_UPLOADING_DATA должен совпадать с sending"
    assert data_kafka_new_processing['recommendation'] == response['recommendation'], "Recommendation в KAFKA_TOPIC_FOR_UPLOADING_DATA должен совпадать с sending"
    assert data_kafka_new_processing['verdict'] == response['verdict'], "Verdict в KAFKA_TOPIC_FOR_UPLOADING_DATA должен совпадать с sending"
