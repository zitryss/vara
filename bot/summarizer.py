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
