from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from bot.summarizer import format_messages, summarize


def test_format_messages_single():
    messages = [
        {"sender": "Alice", "text": "Hello everyone", "timestamp": datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc)},
    ]

    result = format_messages(messages)

    assert result == "[10:30] Alice: Hello everyone"


def test_format_messages_multiple():
    messages = [
        {"sender": "Alice", "text": "Hello", "timestamp": datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc)},
        {"sender": "Bob", "text": "Hi there", "timestamp": datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc)},
    ]

    result = format_messages(messages)

    assert result == "[10:00] Alice: Hello\n[10:01] Bob: Hi there"


def test_format_messages_empty():
    result = format_messages([])

    assert result == ""


@pytest.mark.asyncio
async def test_summarize_calls_openai():
    messages = [
        {"sender": "Alice", "text": "Hello", "timestamp": datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc)},
    ]
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Alice said hello."

    with patch("bot.summarizer.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await summarize(messages)

    assert result == "Alice said hello."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert len(call_kwargs["messages"]) == 2
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_summarize_raises_on_api_error():
    messages = [
        {"sender": "Alice", "text": "Hello", "timestamp": datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc)},
    ]

    with patch("bot.summarizer.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception, match="API error"):
            await summarize(messages)
