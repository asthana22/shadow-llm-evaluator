#!/usr/bin/env python3
import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

CANDIDATES = [
    "openai-gpt-5.5",
    "openai-gpt-5.4",
    "openai-gpt-5",
    "openai-gpt-4o",
    "openai-gpt-4o-mini",
    "openai-gpt-4.1",
    "llama3.3-70b-instruct",
]


async def try_model(client: httpx.AsyncClient, model: str, headers: dict) -> tuple[str, int, str]:
    resp = await client.post(
        "https://inference.do-ai.run/v1/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Say hi in one word."}],
            "max_completion_tokens": 16,
        },
    )
    return model, resp.status_code, resp.text[:200]


async def main() -> None:
    key = os.environ["PRIMARY_LLM_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        for model in CANDIDATES:
            m, status, snippet = await try_model(client, model, headers)
            print(f"{m}: {status} {snippet.replace(chr(10), ' ')}")


if __name__ == "__main__":
    asyncio.run(main())
