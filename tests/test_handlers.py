from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers import collect_message, summary_command, voice_handler
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


def _make_voice_update(chat_id, file_id="file123", first_name="Alice", date=None):
    """Build a minimal mock Telegram Update for a voice message."""
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_chat.type = "group"
    update.message.voice.file_id = file_id
    update.message.from_user.first_name = first_name
    update.message.from_user.last_name = None
    update.message.date = date or datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc)
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_voice_handler_transcribes_and_stores():
    storage = MessageStorage()
    update = _make_voice_update(1)
    context = MagicMock()
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = bytearray(b"fake-audio")
    context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch("bot.handlers.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Hello from voice"

        await voice_handler(update, context, storage=storage)

    mock_transcribe.assert_called_once_with(bytes(bytearray(b"fake-audio")))
    messages = storage.get_and_clear(1)
    assert len(messages) == 1
    assert messages[0]["sender"] == "Alice"
    assert messages[0]["text"] == "Hello from voice"
    update.message.reply_text.assert_called_once_with("**Alice:** Hello from voice")


@pytest.mark.asyncio
async def test_voice_handler_uses_full_name_in_reply():
    storage = MessageStorage()
    update = _make_voice_update(1)
    update.message.from_user.last_name = "Smith"
    context = MagicMock()
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = bytearray(b"fake-audio")
    context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch("bot.handlers.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Hey there"

        await voice_handler(update, context, storage=storage)

    update.message.reply_text.assert_called_once_with("**Alice Smith:** Hey there")
    messages = storage.get_and_clear(1)
    assert messages[0]["sender"] == "Alice Smith"


@pytest.mark.asyncio
async def test_voice_handler_ignores_private_chats():
    storage = MessageStorage()
    update = _make_voice_update(1)
    update.effective_chat.type = "private"
    context = MagicMock()

    await voice_handler(update, context, storage=storage)

    assert storage.is_empty(1)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_voice_handler_error_on_transcription_failure():
    storage = MessageStorage()
    update = _make_voice_update(1)
    context = MagicMock()
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = bytearray(b"fake-audio")
    context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch("bot.handlers.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.side_effect = Exception("Whisper error")

        await voice_handler(update, context, storage=storage)

    update.message.reply_text.assert_called_once_with(
        "Sorry, couldn't transcribe this voice message."
    )
    assert storage.is_empty(1)


@pytest.mark.asyncio
async def test_voice_handler_empty_transcription():
    storage = MessageStorage()
    update = _make_voice_update(1)
    context = MagicMock()
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = bytearray(b"fake-audio")
    context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch("bot.handlers.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ""

        await voice_handler(update, context, storage=storage)

    update.message.reply_text.assert_called_once_with(
        "Couldn't recognize any speech in this voice message."
    )
    assert storage.is_empty(1)
