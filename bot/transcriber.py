import io

import openai


async def transcribe(file_bytes: bytes) -> str:
    client = openai.AsyncOpenAI()
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=("voice.ogg", io.BytesIO(file_bytes)),
    )
    return response.text
