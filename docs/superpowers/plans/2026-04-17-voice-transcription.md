# Voice Message Transcription Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add voice message transcription to the Telegram bot so voice notes are transcribed via Whisper, stored in the summary buffer, and replied with the sender's name.

**Architecture:** New `transcriber.py` module wraps OpenAI Whisper API. New `voice_handler` in `handlers.py` orchestrates download → transcribe → store → reply. Registration in `main.py` via `filters.VOICE`.

**Tech Stack:** OpenAI Whisper API (`whisper-1`), python-telegram-bot voice/file APIs

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `bot/transcriber.py` | Create | Whisper API call — accepts audio bytes, returns transcription |
| `tests/test_transcriber.py` | Create | Unit tests for transcriber |
| `bot/handlers.py` | Modify | Add `voice_handler` function |
| `tests/test_handlers.py` | Modify | Add voice handler tests |
| `bot/main.py` | Modify | Register voice handler |

---

### Task 1: Transcriber Module

**Files:**
- Create: `bot/transcriber.py`
- Create: `tests/test_transcriber.py`

- [ ] **Step 1: Write failing tests for transcriber**

Create `tests/test_transcriber.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_transcriber.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.transcriber'`

- [ ] **Step 3: Implement transcriber**

Create `bot/transcriber.py`:

```python
import io

import openai


async def transcribe(file_bytes: bytes) -> str:
    client = openai.AsyncOpenAI()
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=("voice.ogg", io.BytesIO(file_bytes)),
    )
    return response.text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_transcriber.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bot/transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcriber module with Whisper API integration"
```

---

### Task 2: Voice Handler

**Files:**
- Modify: `bot/handlers.py`
- Modify: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for voice_handler**

Append to `tests/test_handlers.py`. First, update the import line at the top:

Change:
```python
from bot.handlers import collect_message, summary_command
```
To:
```python
from bot.handlers import collect_message, summary_command, voice_handler
```

Then add a voice-specific mock helper and tests at the bottom of the file:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_handlers.py::test_voice_handler_transcribes_and_stores -v`
Expected: FAIL with `ImportError: cannot import name 'voice_handler'`

- [ ] **Step 3: Implement voice_handler**

Add the import to the top of `bot/handlers.py`:

Change:
```python
from bot.summarizer import summarize
```
To:
```python
from bot.summarizer import summarize
from bot.transcriber import transcribe
```

Then add the `voice_handler` function at the end of `bot/handlers.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_handlers.py -v`
Expected: All 11 tests PASS (6 existing + 5 new).

- [ ] **Step 5: Commit**

```bash
git add bot/handlers.py tests/test_handlers.py
git commit -m "feat: add voice_handler for voice message transcription"
```

---

### Task 3: Wire Voice Handler in main.py

**Files:**
- Modify: `bot/main.py`

- [ ] **Step 1: Update import in main.py**

Change:
```python
from bot.handlers import collect_message, summary_command
```
To:
```python
from bot.handlers import collect_message, summary_command, voice_handler
```

- [ ] **Step 2: Register voice handler**

Add the voice handler registration after the existing text message handler. After line 50 (the closing paren of the text MessageHandler), add:

```python
    app.add_handler(
        MessageHandler(
            filters.VOICE,
            partial(voice_handler, storage=storage),
        )
    )
```

- [ ] **Step 3: Verify syntax**

Run: `./venv/bin/python -c "import ast; ast.parse(open('bot/main.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run full test suite**

Run: `./venv/bin/pytest tests/ -v`
Expected: All 23 tests PASS (17 existing + 3 transcriber + 5 voice handler - but total is 6+5+3+5+... let me count: 6 storage + 5 summarizer + 11 handlers + 3 transcriber = 25 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/main.py
git commit -m "feat: register voice handler in main entry point"
```
