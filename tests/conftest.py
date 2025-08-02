import asyncio
import os
import threading
import time
from redis import Redis
from dotenv import load_dotenv

from srt.dependencies.redis_dependencies import RedisWrapper

load_dotenv()  # Загружает переменные из .env
KAFKA_BOOTSTRAP_SERVERS=os.getenv('KAFKA_BOOTSTRAP_SERVERS')
KAFKA_TOPIC_FOR_UPLOADING_DATA=os.getenv('KAFKA_TOPIC_FOR_UPLOADING_DATA')
KAFKA_TOPIC_FOR_AI_HANDLER=os.getenv('KAFKA_TOPIC_FOR_AI_HANDLER')
KAFKA_TOPIC_FOR_NOTIFICATIONS=os.getenv('KAFKA_TOPIC_FOR_NOTIFICATIONS')

# этот импорт необходимо указывать именно тут для корректного импорта .tests.env
import pytest_asyncio
from confluent_kafka.cimpl import NewTopic, TopicPartition
from confluent_kafka import Consumer

from srt.config import logger
from srt.dependencies.kafka_dependencies import admin_client, consumer_ai_handler

REQUIREMENTS ="""
Должность: Middle Python Backend Developer
Зарплата: от 150 000 руб.

Обязательные требования:
Опыт коммерческой разработки на Python 3+ от 2 лет.
Глубокие знания Django или FastAPI.
Работа с PostgreSQL/MySQL (оптимизация запросов, индексы).
Опыт с Docker (развертывание, compose).
Понимание REST API, GraphQL.

Желательные навыки:
Redis (кеширование, Celery).
Kubernetes (базовое понимание).
Знание тестирования (pytest, unit tests).
Английский — уровень B1+ (чтение документации).

Что будет минусом:
Нет опыта с Docker.
Только Flask (без Django/FastAPI).
Отсутствие работы с базами данных.
"""

RESUME_BY_20_POINT = """
ФИО: Смирнов Дмитрий Александрович
Контакты: +7 (123) 456-78-90, smirnov.d@mail.ru
Цель: Разработчик Python (стажер)

Опыт работы:
Веб-разработчик (Frontend), ООО "ТехноСтарт"
01.2022 - настоящее время
Разработка интерфейсов на React.js
Верстка по макетам Figma
Написание простых скриптов на Python для автоматизации тестирования

Навыки:
JavaScript (ES6+), React
HTML5, CSS3, Bootstrap
Базовый Python (написание скриптов)
MySQL (простые запросы)
Git (основные команды)

Образование:
Онлайн-курсы "Веб-разработчик с нуля", 2021 (6 месяцев)

Дополнительно:
Английский: A2 (базовый)
Участвовал в школьном хакатоне по программированию
"""

RESUME_BY_60_POINT = """
ФИО: Петров Иван Сергеевич
Контакты: +7 (555) 123-45-67, petrov.dev@yandex.ru

Опыт работы:
Python Developer, ООО "ТехноСофт"
05.2020 - настоящее время
Разработка backend на Django (DRF)
Оптимизация SQL-запросов (sqlite3)
Интеграция с платежными системами
Настройка Docker-контейнеров

Ключевые проекты:
Система электронных заказов (Django + Celery)
API для мобильного приложения (DRF + JWT)

Навыки:
Python (Django, DRF)
sqlite3, Redis
Docker, Docker-compose
Git, Linux

Образование:
Национальный Исследовательский Университет, магистр "Прикладная информатика", 2018-2020
"""

RESUME_BY_100_POINT = """
ФИО: Волков Алексей Дмитриевич
Контакты: +7 (916) 999-88-77, a.volkov@career.habr

Опыт работы:
Senior Python Developer, Тинькофф
06.2018 - настоящее время
Архитектура высоконагруженных сервисов
Разработка сложных API на Django и FastAPI
Оптимизация запросов к PostgreSQL
Внедрение Kubernetes в production
Наставничество junior-разработчиков

Технические навыки:
Python (Django, FastAPI, asyncio)
PostgreSQL, Redis, Kafka
Docker, Kubernetes, Helm
Git, GitLab CI/CD
Prometheus, Grafana

Образование:
PhD in Computer Science, MIT, 2014-2018
MSc in Software Engineering, МФТИ, 2012-2014

Публикации:
3 статьи по оптимизации баз данных в международных журналах

Языки:
Английский: C1 (Advanced)
"""


TOPIC_LIST = [
    KAFKA_TOPIC_FOR_UPLOADING_DATA,
    KAFKA_TOPIC_FOR_AI_HANDLER,
    KAFKA_TOPIC_FOR_NOTIFICATIONS
]

conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'test-group-' + str(os.getpid()),  # Уникальный group.id для каждого запуска тестов
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': 'false',  # Отключаем авто-коммит
    'isolation.level': 'read_committed'
}

consumer = Consumer(conf)

@pytest_asyncio.fixture(scope='session', autouse=True)
async def start_kafka_consumer():
    """Фикстура для запуска потребителя Kafka в отдельном потоке"""
    consumer_thread = threading.Thread(target=consumer_ai_handler.consumer_run)
    consumer_thread.daemon = True  # Демонизируем поток, чтобы он завершился при завершении основного потока
    consumer_thread.start()
    yield

@pytest_asyncio.fixture(scope='session', autouse=True)
async def check_kafka_connection(_session_scoped_runner):
    try:
        admin_client.list_topics(timeout=10)
    except Exception:
        raise Exception("Не удалось установить соединение с Kafka!")

@pytest_asyncio.fixture(scope='function')
async def clearing_kafka():
    """Очищает топик у kafka с которым работаем, путём его пересоздания"""
    max_retries = 10
    consumer.unsubscribe()

    # Сбрасываем позицию consumer перед очисткой
    for topic in TOPIC_LIST:
        try:
            consumer.assign([TopicPartition(topic, 0, 0)])
            consumer.seek(TopicPartition(topic, 0, 0))
        except Exception as e:
            logger.warning(f"Failed to reset consumer for topic {topic}: {e}")

    for topic in TOPIC_LIST:
        admin_client.delete_topics([topic])

    # Ждём подтверждения удаления
    for _ in range(max_retries):
        meta = admin_client.list_topics(timeout=5)
        if all(t not in meta.topics for t in TOPIC_LIST):
            break
        time.sleep(1)
    else:
        logger.warning(f"Топик всё ещё существует после попыток удаления.")

    # Создаём топики
    for topic in TOPIC_LIST:
        admin_client.create_topics([NewTopic(topic=topic, num_partitions=1, replication_factor=1)])

    time.sleep(2)

    # Ждём инициализации partition и leader
    for _ in range(max_retries):
        meta_data = admin_client.list_topics(timeout=5)
        ready = True
        for topic in TOPIC_LIST:
            topic_meta = meta_data.topics.get(topic)
            if not topic_meta or topic_meta.error:
                ready = False
                break
            partitions = topic_meta.partitions
            if 0 not in partitions or partitions[0].leader == -1:
                ready = False
                break
        if ready:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Partition или leader не инициализирован после создания топика.")

    # подписка на новый топик
    consumer_ai_handler.subscribe_topics([KAFKA_TOPIC_FOR_AI_HANDLER])