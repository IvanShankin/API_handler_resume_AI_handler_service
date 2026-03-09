import asyncio

from src.app import start_app


async def main():
    async with start_app():
        print("Приложение запущено, ожидаем событий...")

        # Чтобы приложение работало постоянно
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())