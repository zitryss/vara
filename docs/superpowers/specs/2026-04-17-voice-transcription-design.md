# Voice Message Transcription — Design Spec

## Overview

Add voice message recognition to the Telegram summary bot. When a user sends a voice message in a group, the bot transcribes it using OpenAI Whisper API, stores the transcription in the message buffer (so it's included in `/summary`), and replies in the group with "**Username:** transcription".

## Tech Stack Addition

- **OpenAI Whisper API** (`whisper-1` model) — uses the existing `OPENAI_API_KEY`, no new credentials needed

## Architecture

Extends the existing bot with two changes:

1. **New module `bot/transcriber.py`** — wraps the Whisper API call
2. **New handler `voice_handler` in `bot/handlers.py`** — orchestrates download, transcription, storage, and reply
3. **Updated `bot/main.py`** — registers the voice handler

```
Voice Message --> Bot
                   └── voice_handler
                         ├── Download .ogg file via Telegram Bot API
                         ├── transcriber.transcribe(file_bytes) → text
                         ├── storage.add(group_id, sender, text, timestamp)
                         └── reply_text("**Sender:** transcription")
```

No changes to `storage.py` or `summarizer.py`. Transcribed voice messages become regular text entries in the buffer.

## New File

### transcriber.py — Whisper API Integration

- Function `async transcribe(file_bytes: bytes) -> str`
- Sends audio bytes to OpenAI Whisper API (`whisper-1` model)
- Telegram voice messages are `.ogg` format — Whisper handles this natively, no conversion needed
- Returns the transcription text
- Language auto-detected by Whisper

## Modified Files

### handlers.py — New voice_handler

- `async voice_handler(update, context, *, storage)` — follows existing handler pattern
- Extracts sender name using the same first_name + optional last_name logic as `collect_message`
- Downloads voice file: `voice = update.message.voice` → `file = await context.bot.get_file(voice.file_id)` → `file_bytes = await file.download_as_bytearray()`
- Calls `transcriber.transcribe(file_bytes)` to get text
- Stores in buffer: `storage.add(group_id, sender, text, timestamp)`
- Replies: `await update.message.reply_text(f"**{sender}:** {text}")`
- Only processes group chats (same private chat filter as `collect_message`)

### main.py — Register Voice Handler

- Add `MessageHandler(filters.VOICE, partial(voice_handler, storage=storage))`

## Error Handling

| Scenario | Behavior |
|---|---|
| Whisper API failure | Reply "Sorry, couldn't transcribe this voice message." Nothing stored. |
| Empty transcription (silence/unintelligible) | Reply "Couldn't recognize any speech in this voice message." Nothing stored. |
| File download failure | Same error reply, nothing stored. |
| Large voice messages | Not a concern — Telegram limit (20MB) is within Whisper limit (25MB). |

## Scope

- Voice messages only — no video notes, no audio files
- Auto-detect language
- No new environment variables or dependencies needed
