# Микросервис обработки AI запросов

ОБЯЗАТЕЛЬНО ОТПРАВЛЯТЬ ЗАПРОСЫ К GPT НЕ С ТЕРРИТОРИИ РФ

## Описание

Этот микросервис предоставляет функциональность для:
- Обработки резюме кандидатов с использованием AI (GPT-4)
- Оценки соответствия резюме требованиям вакансий
- Взаимодействия с другими сервисами через Kafka
- Кэширования результатов обработки в Redis

## Основные функции
- Получение запросов на обработку резюме через Kafka
- Интеграция с OpenAI API для анализа резюме
- Отправка результатов обработки в два топика Kafka:
  - `notifications` - полные данные с callback_url
  - `uploading_data` - данные для сохранения в БД (без callback_url)
- Защита от повторной обработки сообщений через Redis

## Технологический стек
- **Python 3.13.3**
- **asyncio** - асинхронная обработка
- **Redis** - кэширование и предотвращение дублирования обработки
- **Kafka** + **confluent-kafka** - взаимодействие с другими сервисами
- **OpenAI API** - анализ резюме
- **Pytest** - тестирование

## Запуск сервиса

### Требования
- Docker и Docker Compose
- Python 3.10+
- Доступ к OpenAI API

### Установка
1. Клонируйте репозиторий
2. Выполните: `pip install -r requirements.txt`
3. Создайте файл `.env` и `.test.env`(для тестирования) на основе `.env.example`
4. Заполните необходимые переменные окружения (особенно `OPENAI_KEY`)

### Запуск
```bash
docker-compose up -d
```

## Тестирование
Для запуска тестов:
```bash
pytest
```
Для запуска тестов через Docker:
```bash
docker-compose --env-file .test.env up -d 
```
```bash
docker-compose --env-file .test.env exec app pytest
```

Тесты покрывают:
- Unit-тесты основных функций AI обработки
- Интеграционные тесты работы с Kafka
- Тесты работы с Redis

## Логирование
Логи сохраняются в файл `logs/auth_service.log` с ротацией по дням.

## Конфигурация
Основные настройки сервиса находятся в:
- `config.py` - лимиты запросов и параметры работы с AI
- `.env` - переменные окружения (Kafka, Redis, OpenAI)

## Ограничения
- Максимальное количество запросов в минуту (RPM): 3
- Максимальное количество запросов в день (RPD): 200
- Лимит токенов в минуту (TPM): 40000

## Redis хранилище
**Ключ:** `processed_messages:{processing_id}`  
**Значение:** `'_'` (метка)  
**Назначение:** Исключение повторной обработки сообщений  
**TTL:** 3 дня

## Kafka взаимодействие

### Получаемые сообщения
**Топик:** `AI_handler`  
**Ключ:** `new_request`  
```json
{
  "callback_url": "str",
  "processing_id": int,
  "user_id": int,
  "resume_id": int,
  "requirements_id": int,
  "requirements": "str",
  "resume": "str"
}
```

### Отправляемые сообщения
1. **Топик:** `notifications`  
   **Ключ:** `new_notifications`  
   ```json
   {
     "success": bool,
     "response": {
       "callback_url": "str",
       "processing_id": int,
       "user_id": int,
       "resume_id": int,
       "requirements_id": int,
       "score": int,
       "matches": ["str"],
       "recommendation": "str",
       "verdict": "str"
     },
     "message_error": "str",
     "wait_seconds": int
   }
   ```

2. **Топик:** `uploading_data`  
   **Ключ:** `new_processing`  
   ```json
   {
     "processing_id": int,
     "user_id": int,
     "resume_id": int,
     "requirements_id": int,
     "score": int,
     "matches": ["str"],
     "recommendation": "str",
     "verdict": "str"
   }
   ```
   
### Общий readme: https://github.com/IvanShankin/API_handler_resume_general_readme