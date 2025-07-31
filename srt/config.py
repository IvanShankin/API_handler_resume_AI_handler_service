import logging
from datetime import timedelta
from pathlib import Path

GPT_MODEL = 'gpt-4.1-mini-2025-04-14'

# ограничение по запросам
RPM = 3 # в минуту
RPD = 200 # в день

# Ограничение токенов (символов). Это действует на входящий и выходящий запрос
TPM = 40000 # в минуту

MIN_COMMIT_COUNT_KAFKA = 10

# данные для ключей Kafka (CONSUMER)
KEY_NEW_REQUEST = 'new_request'

# данные для ключей Kafka (PRODUCER)
KEY_NEW_SENDING = 'new_sending'
KEY_NEW_PROCESSING= 'new_processing'

STORAGE_TIME_PROCESSED_MESSAGES = timedelta(days=3) # время хранения обработанного сообщения

LOG_DIR = Path("../logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "auth_service.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)