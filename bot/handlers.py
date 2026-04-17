import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.storage import MessageStorage
from bot.summarizer import summarize
from bot.transcriber import transcribe

logger = logging.getLogger(__name__)


async def collect_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    storage: MessageStorage,
) -> None:
    if update.effective_chat.type == "private":
        return

    user = update.message.from_user
    sender = user.first_name
    if user.last_name:
        sender += f" {user.last_name}"

    storage.add(
        group_id=update.effective_chat.id,
        sender=sender,
        text=update.message.text,
        timestamp=update.message.date,
    )


async def summary_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    storage: MessageStorage,
) -> None:
    group_id = update.effective_chat.id

    if storage.is_empty(group_id):
        await update.message.reply_text(
            "Nothing to summarize since the last summary."
        )
        return

    messages = storage.get_and_clear(group_id)

    try:
        result = await summarize(messages)
    except Exception:
        logger.exception("Failed to generate summary for group %s", group_id)
        storage._buffers[group_id] = messages
        await update.message.reply_text(
            "Sorry, couldn't generate a summary right now. Try again later."
        )
        return

    await update.message.reply_text(result)


async def voice_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    storage: MessageStorage,
) -> None:
    if update.effective_chat.type == "private":
        return

    user = update.message.from_user
    sender = user.first_name
    if user.last_name:
        sender += f" {user.last_name}"

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_bytes = bytes(await file.download_as_bytearray())
        text = await transcribe(file_bytes)
    except Exception:
        logger.exception("Failed to transcribe voice message in group %s", update.effective_chat.id)
        await update.message.reply_text(
            "Sorry, couldn't transcribe this voice message."
        )
        return

    if not text:
        await update.message.reply_text(
            "Couldn't recognize any speech in this voice message."
        )
        return

    storage.add(
        group_id=update.effective_chat.id,
        sender=sender,
        text=text,
        timestamp=update.message.date,
    )

    await update.message.reply_text(f"**{sender}:** {text}")
