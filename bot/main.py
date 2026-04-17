import logging
import os
import sys
from functools import partial

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import collect_message, summary_command, voice_handler
from bot.storage import MessageStorage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)
    if not openai_key:
        logger.error("OPENAI_API_KEY is not set")
        sys.exit(1)

    # openai reads OPENAI_API_KEY from env automatically

    logger.warning(
        "Message buffer is in-memory only. Messages will be lost on restart."
    )

    storage = MessageStorage()

    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(
        CommandHandler("summary", partial(summary_command, storage=storage))
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            partial(collect_message, storage=storage),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.VOICE,
            partial(voice_handler, storage=storage),
        )
    )

    logger.info("Bot started. Polling for updates...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
