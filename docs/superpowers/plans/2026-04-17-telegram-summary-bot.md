# Telegram Group Summary Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python Telegram bot that collects group messages in memory and generates AI-powered summaries on demand via `/summary`.

**Architecture:** Single-process long-polling bot using `python-telegram-bot`. Messages buffered in an in-memory dict keyed by group ID. `/summary` command sends the buffer to OpenAI `gpt-4o-mini` for summarization, posts the result, and clears the buffer.

**Tech Stack:** Python 3.12+, python-telegram-bot >=21.0, openai >=1.0, python-dotenv >=1.0, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `bot/__init__.py` | Package marker |
| `bot/storage.py` | `MessageStorage` class — in-memory per-group message buffer |
| `bot/summarizer.py` | `summarize()` — formats messages + calls OpenAI API |
| `bot/handlers.py` | Telegram handlers — message collector + `/summary` command |
| `bot/main.py` | Entry point — loads config, wires handlers, starts polling |
| `tests/__init__.py` | Test package marker |
| `tests/test_storage.py` | Unit tests for `MessageStorage` |
| `tests/test_summarizer.py` | Unit tests for `summarize()` |
| `tests/test_handlers.py` | Unit tests for Telegram handlers |
| `.env.example` | Template for required environment variables |
| `requirements.txt` | Python dependencies |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `bot/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
python-telegram-bot>=21.0
openai>=1.0
python-dotenv>=1.0
pytest>=8.0
```

- [ ] **Step 2: Create `.env.example`**

```
TELEGRAM_BOT_TOKEN=your-bot-token-here
OPENAI_API_KEY=your-openai-api-key-here
```

- [ ] **Step 3: Create empty package files**

Create `bot/__init__.py` and `tests/__init__.py` as empty files.

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example bot/__init__.py tests/__init__.py
git commit -m "chore: scaffold project with dependencies and package structure"
```

---

### Task 2: MessageStorage

**Files:**
- Create: `bot/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests for MessageStorage**

Create `tests/test_storage.py`:

```python
from datetime import datetime, timezone

from bot.storage import MessageStorage


def test_add_and_get_messages():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    storage.add(1, "Bob", "Hi there", datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc))

    messages = storage.get_and_clear(1)

    assert len(messages) == 2
    assert messages[0]["sender"] == "Alice"
    assert messages[0]["text"] == "Hello"
    assert messages[1]["sender"] == "Bob"
    assert messages[1]["text"] == "Hi there"


def test_get_and_clear_empties_buffer():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    storage.get_and_clear(1)
    messages = storage.get_and_clear(1)

    assert messages == []


def test_is_empty_returns_true_for_new_group():
    storage = MessageStorage()

    assert storage.is_empty(999) is True


def test_is_empty_returns_false_after_add():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    assert storage.is_empty(1) is False


def test_is_empty_returns_true_after_clear():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    storage.get_and_clear(1)

    assert storage.is_empty(1) is True


def test_multiple_groups_are_independent():
    storage = MessageStorage()
    storage.add(1, "Alice", "Group 1 msg", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    storage.add(2, "Bob", "Group 2 msg", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    messages_1 = storage.get_and_clear(1)
    messages_2 = storage.get_and_clear(2)

    assert len(messages_1) == 1
    assert messages_1[0]["sender"] == "Alice"
    assert len(messages_2) == 1
    assert messages_2[0]["sender"] == "Bob"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.storage'`

- [ ] **Step 3: Implement MessageStorage**

Create `bot/storage.py`:

```python
from datetime import datetime


class MessageStorage:
    def __init__(self) -> None:
        self._buffers: dict[int, list[dict]] = {}

    def add(self, group_id: int, sender: str, text: str, timestamp: datetime) -> None:
        if group_id not in self._buffers:
            self._buffers[group_id] = []
        self._buffers[group_id].append({
            "sender": sender,
            "text": text,
            "timestamp": timestamp,
        })

    def get_and_clear(self, group_id: int) -> list[dict]:
        return self._buffers.pop(group_id, [])

    def is_empty(self, group_id: int) -> bool:
        return len(self._buffers.get(group_id, [])) == 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bot/storage.py tests/test_storage.py
git commit -m "feat: add MessageStorage for in-memory per-group message buffering"
```

---

### Task 3: Summarizer

**Files:**
- Create: `bot/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests for summarizer**

Create `tests/test_summarizer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_summarizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.summarizer'`

- [ ] **Step 3: Implement summarizer**

Create `bot/summarizer.py`:

```python
import logging

import openai

SYSTEM_PROMPT = (
    "You are a concise summarizer. Summarize the following group chat conversation, "
    "highlighting key topics, decisions, and action items."
)

# Rough limit: ~100k tokens ≈ ~400k characters for gpt-4o-mini
MAX_CHAT_LOG_CHARS = 400_000

logger = logging.getLogger(__name__)


def format_messages(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        timestamp = msg["timestamp"].strftime("%H:%M")
        lines.append(f"[{timestamp}] {msg['sender']}: {msg['text']}")
    return "\n".join(lines)


async def summarize(messages: list[dict]) -> str:
    chat_log = format_messages(messages)

    trimmed = False
    while len(chat_log) > MAX_CHAT_LOG_CHARS:
        messages = messages[len(messages) // 4:]
        chat_log = format_messages(messages)
        trimmed = True

    user_content = chat_log
    if trimmed:
        user_content = (
            "[Note: Older messages were trimmed due to length.]\n\n" + chat_log
        )

    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Install pytest-asyncio**

Add `pytest-asyncio>=0.24` to `requirements.txt` and run:

Run: `pip install pytest-asyncio>=0.24`
Expected: Package installs successfully.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_summarizer.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add bot/summarizer.py tests/test_summarizer.py requirements.txt
git commit -m "feat: add summarizer module with OpenAI integration"
```

---

### Task 4: Telegram Handlers

**Files:**
- Create: `bot/handlers.py`
- Create: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for handlers**

Create `tests/test_handlers.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot.handlers'`

- [ ] **Step 3: Implement handlers**

Create `bot/handlers.py`:

```python
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.storage import MessageStorage
from bot.summarizer import summarize

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bot/handlers.py tests/test_handlers.py
git commit -m "feat: add Telegram handlers for message collection and /summary"
```

---

### Task 5: Main Entry Point

**Files:**
- Create: `bot/main.py`

- [ ] **Step 1: Implement main.py**

Create `bot/main.py`:

```python
import logging
import os
import sys
from functools import partial

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import collect_message, summary_command
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

    logger.info("Bot started. Polling for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax is valid**

Run: `python -c "import ast; ast.parse(open('bot/main.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/main.py
git commit -m "feat: add main entry point with config loading and handler wiring"
```

---

### Task 6: Run All Tests and Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All 17 tests PASS.

- [ ] **Step 2: Verify the bot module is importable**

Run: `python -c "from bot.main import main; print('Import OK')"`
Expected: `Import OK` (requires `.env` with valid tokens for actual runtime, but import should work).

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final verification — all tests passing"
```
