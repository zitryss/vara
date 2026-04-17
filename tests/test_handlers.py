from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers import collect_message, summary_command
from bot.storage import MessageStorage


def _make_update(chat_id, text, first_name="Alice", date=None):
    """Build a minimal mock Telegram Update."""
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_chat.type = "group"
    update.message.text = text
    update.message.from_user.first_name = first_name
    update.message.from_user.last_name = None
    update.message.date = date or datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc)
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_collect_message_stores_text():
    storage = MessageStorage()
    update = _make_update(1, "Hello everyone")
    context = MagicMock()

    await collect_message(update, context, storage=storage)

    assert not storage.is_empty(1)
    messages = storage.get_and_clear(1)
    assert len(messages) == 1
    assert messages[0]["sender"] == "Alice"
    assert messages[0]["text"] == "Hello everyone"


@pytest.mark.asyncio
async def test_collect_message_uses_full_name():
    storage = MessageStorage()
    update = _make_update(1, "Hi")
    update.message.from_user.last_name = "Smith"
    context = MagicMock()

    await collect_message(update, context, storage=storage)

    messages = storage.get_and_clear(1)
    assert messages[0]["sender"] == "Alice Smith"


@pytest.mark.asyncio
async def test_collect_message_ignores_private_chats():
    storage = MessageStorage()
    update = _make_update(1, "Hello")
    update.effective_chat.type = "private"
    context = MagicMock()

    await collect_message(update, context, storage=storage)

    assert storage.is_empty(1)


@pytest.mark.asyncio
async def test_summary_command_empty_buffer():
    storage = MessageStorage()
    update = _make_update(1, "/summary")
    context = MagicMock()

    await summary_command(update, context, storage=storage)

    update.message.reply_text.assert_called_once_with(
        "Nothing to summarize since the last summary."
    )


@pytest.mark.asyncio
async def test_summary_command_calls_summarizer():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    update = _make_update(1, "/summary")
    context = MagicMock()

    with patch("bot.handlers.summarize", new_callable=AsyncMock) as mock_summarize:
        mock_summarize.return_value = "Alice greeted the group."

        await summary_command(update, context, storage=storage)

    mock_summarize.assert_called_once()
    update.message.reply_text.assert_called_once_with("Alice greeted the group.")
    assert storage.is_empty(1)


@pytest.mark.asyncio
async def test_summary_command_preserves_buffer_on_error():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    update = _make_update(1, "/summary")
    context = MagicMock()

    with patch("bot.handlers.summarize", new_callable=AsyncMock) as mock_summarize:
        mock_summarize.side_effect = Exception("API error")

        await summary_command(update, context, storage=storage)

    update.message.reply_text.assert_called_once_with(
        "Sorry, couldn't generate a summary right now. Try again later."
    )
    assert not storage.is_empty(1)
