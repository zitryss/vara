# Telegram Group Summary Bot — Design Spec

## Overview

A Python Telegram bot that passively collects messages in group chats and generates an AI-powered summary on demand via the `/summary` command. Summaries cover all messages since the last summary was requested.

## Tech Stack

- **Python 3.12+**
- **python-telegram-bot** — Telegram Bot API framework (long-polling)
- **openai** — Official OpenAI Python SDK
- **python-dotenv** — Environment variable loading from `.env`

## Architecture

Single-process bot with three responsibilities:

1. **Message collector** — listens to all text messages, buffers them in memory per group
2. **Summary command handler** — on `/summary`, sends buffered messages to OpenAI, posts result, clears buffer
3. **Config** — loads `TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY` from environment variables

```
Group Chat --> Bot (long-polling)
                ├── MessageHandler -> in-memory buffer (dict[group_id, list[message]])
                └── /summary CommandHandler -> OpenAI API -> reply in group
```

No database, no web server, no background jobs.

## Project Structure

```
vara/
├── bot/
│   ├── __init__.py
│   ├── main.py          # Entry point, builds Application, registers handlers
│   ├── handlers.py      # Message collector + /summary command handler
│   ├── storage.py       # In-memory message buffer (per-group dict)
│   └── summarizer.py    # OpenAI API call to generate summary
├── .env.example          # Template for required env vars
├── requirements.txt
└── README.md
```

## Components

### storage.py — In-Memory Message Buffer

- A class `MessageStorage` wrapping `dict[int, list[dict]]` (group_id -> messages)
- Each message stored as `{"sender": str, "text": str, "timestamp": datetime}`
- Methods:
  - `add(group_id, sender, text, timestamp)` — append a message
  - `get_and_clear(group_id) -> list[dict]` — return all messages for a group and clear the buffer
  - `is_empty(group_id) -> bool` — check if there are buffered messages

### handlers.py — Telegram Handlers

**Message collector:**
- Registered as a `MessageHandler` with a text filter
- On every text message in a group, extracts sender display name, text, and timestamp
- Calls `storage.add(group_id, sender, text, timestamp)`

**Summary command handler:**
- Registered as a `CommandHandler` for `/summary`
- Reads buffered messages via `storage.get_and_clear(group_id)`
- If empty: replies "Nothing to summarize since the last summary."
- Otherwise: passes messages to `summarizer.summarize()`, posts the result
- On summarizer failure: replies with an error message and does **not** clear the buffer

### summarizer.py — OpenAI Summarization

- Function `summarize(messages: list[dict]) -> str`
- Formats messages into a chat log string: `[HH:MM] Sender: text`
- System prompt: "You are a concise summarizer. Summarize the following group chat conversation, highlighting key topics, decisions, and action items."
- Uses `gpt-4o-mini` model (cost-effective for summarization)
- Truncates oldest messages if the formatted log exceeds ~100k tokens to stay within context limits

### main.py — Entry Point

- Loads environment variables via `python-dotenv`
- Validates that `TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY` are set
- Builds `python-telegram-bot` Application
- Registers message collector and `/summary` command handler
- Starts long-polling via `application.run_polling()`

## Error Handling

| Scenario | Behavior |
|---|---|
| OpenAI API failure | Reply "Sorry, couldn't generate a summary right now. Try again later." Buffer is preserved. |
| Token limit exceeded | Truncate oldest messages, note in summary that older messages were trimmed. |
| No messages since last summary | Reply "Nothing to summarize since the last summary." |
| Bot restart | Buffer lost. Accepted trade-off for in-memory storage. Warning logged on startup. |
| Non-text messages | Silently skipped — only text messages are collected. |

## Configuration

Environment variables loaded from `.env`:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `OPENAI_API_KEY` | Yes | OpenAI API key |

## Access Control

- Anyone in the group can call `/summary`
- No admin restrictions

## Multi-Group Support

- Buffer is keyed by `group_id`, so the bot works across multiple groups simultaneously
- Each group has independent message history and summary state

## Dependencies

```
python-telegram-bot>=21.0
openai>=1.0
python-dotenv>=1.0
```
