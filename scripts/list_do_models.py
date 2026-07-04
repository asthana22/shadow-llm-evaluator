#!/usr/bin/env python3
"""Resolve a usable DO inference model id (prefers openai/gpt*)."""
import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("PRIMARY_LLM_API_KEY", "")
BASE = "https://inference.do-ai.run/v1"


async def main() -> int:
    if not API_KEY:
        print("PRIMARY_LLM_API_KEY not set", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE}/models", headers=headers)
        if resp.status_code != 200:
            print(f"models list failed: {resp.status_code} {resp.text[:500]}", file=sys.stderr)
            return 1

        models = resp.json().get("data", [])
        ids = [m.get("id", "") for m in models]
        gpt = [m for m in ids if "gpt" in m.lower()]
        print("gpt_models:", gpt[:20] if gpt else "none")
        print("total_models:", len(ids))
        if gpt:
            print("recommended:", gpt[0])
        elif ids:
            print("recommended:", ids[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
