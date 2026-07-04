#!/usr/bin/env python3
"""Smoke-test POST /v1/chat against a running local server."""
import asyncio
import json
import sys

import httpx


async def main() -> int:
    payload = {
        "model": "llama3.3-70b-instruct",
        "prompt": "Reply with JSON only: {\"action\": \"greet\", \"message\": \"hello\"}",
        "max_completion_tokens": 128,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "http://127.0.0.1:8080/v1/chat",
            json=payload,
        )
    print("status:", resp.status_code)
    print("x-request-id:", resp.headers.get("x-request-id"))
    try:
        body = resp.json()
        print("body:", json.dumps(body, indent=2)[:1500])
    except json.JSONDecodeError:
        print("body:", resp.text[:1500])
    return 0 if resp.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
