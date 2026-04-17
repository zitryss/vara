from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.transcriber import transcribe


@pytest.mark.asyncio
async def test_transcribe_returns_text():
    mock_response = MagicMock()
    mock_response.text = "Hello, this is a voice message."

    with patch("bot.transcriber.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await transcribe(b"fake-audio-bytes")

    assert result == "Hello, this is a voice message."
    mock_client.audio.transcriptions.create.assert_called_once()
    call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
    assert call_kwargs["model"] == "whisper-1"


@pytest.mark.asyncio
async def test_transcribe_raises_on_api_error():
    with patch("bot.transcriber.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception, match="API error"):
            await transcribe(b"fake-audio-bytes")


@pytest.mark.asyncio
async def test_transcribe_returns_empty_string_for_silence():
    mock_response = MagicMock()
    mock_response.text = ""

    with patch("bot.transcriber.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await transcribe(b"fake-audio-bytes")

    assert result == ""
