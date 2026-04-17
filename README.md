# Vara

A Telegram bot that helps a group of friends track and split bills. It listens to group conversations (text and voice messages), and generates concise summaries on demand highlighting who owes what.

## Features

- Collects text messages in group chats
- Transcribes voice messages using OpenAI Whisper and replies with the transcription
- Generates conversation summaries via `/summary` command using OpenAI GPT
- Tracks messages since the last summary per group

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) and disable privacy mode (`/setprivacy` -> Disable)
2. Copy `.env.example` to `.env` and fill in your tokens:
   ```
   TELEGRAM_BOT_TOKEN=your-bot-token
   OPENAI_API_KEY=your-openai-key
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```
   python -m bot.main
   ```

## Usage

Add the bot to a group chat. It will silently collect messages. When anyone sends `/summary`, the bot posts a summary of all messages since the last summary.

Voice messages are automatically transcribed and included in summaries.
