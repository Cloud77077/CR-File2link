"""Application entry point.

Runs:
1) Pyrogram Telegram bot client
2) FastAPI HTTP server for file links
"""

from __future__ import annotations

import asyncio
import logging
import signal

import uvicorn
from dotenv import load_dotenv
from pyrogram import Client

from bot.config import Settings
from bot.database import Database
from bot.handlers import register_handlers
from server.api import create_app


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def run_bot(client: Client, stop_event: asyncio.Event) -> None:
    await client.start()
    logging.getLogger(__name__).info("Telegram bot started.")
    try:
        await stop_event.wait()
    finally:
        await client.stop()
        logging.getLogger(__name__).info("Telegram bot stopped.")


async def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    db = Database(str(settings.database_path))
    await db.connect()
    await db.init_schema()

    bot_client = Client(
        name="telegram-file-link-bot",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
        workdir=str(settings.pyrogram_workdir),
    )
    register_handlers(bot_client, settings, db)

    fastapi_app = create_app(settings, db)
    uvicorn_config = uvicorn.Config(
        app=fastapi_app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        loop="asyncio",
    )
    api_server = uvicorn.Server(uvicorn_config)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Signal handlers are not available on some platforms.
            pass

    bot_task = asyncio.create_task(run_bot(bot_client, stop_event))
    api_task = asyncio.create_task(api_server.serve())

    done, pending = await asyncio.wait(
        {bot_task, api_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in done:
        if task.exception():
            logging.getLogger(__name__).exception("Task failed", exc_info=task.exception())

    stop_event.set()
    api_server.should_exit = True

    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
