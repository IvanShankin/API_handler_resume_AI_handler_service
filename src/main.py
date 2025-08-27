import asyncio

from src.dependencies.kafka_dependencies import consumer_ai_handler

if __name__ == "__main__":
    asyncio.run(consumer_ai_handler.consumer_run())