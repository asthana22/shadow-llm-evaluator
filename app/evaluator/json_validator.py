import json
from typing import Any


def _parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _action_from_payload(payload: Any) -> tuple[bool, str | None]:
    if not isinstance(payload, dict):
        return False, None
    action = payload.get("action")
    if not isinstance(action, str):
        return False, None
    return True, action


def extract_action_from_llm_response(response_text: str) -> tuple[bool, str | None]:
    """
    Parse a chat-completion body and extract `action` from assistant message content.

    Supports:
    - OpenAI/DO format: choices[0].message.content as JSON string
    - Flat JSON body with top-level `action`
    """
    outer = _parse_json(response_text)
    if outer is None:
        return False, None

    # Flat JSON {"action": "..."}
    valid, action = _action_from_payload(outer)
    if valid:
        return True, action

    if not isinstance(outer, dict):
        return False, None

    choices = outer.get("choices")
    if not isinstance(choices, list) or not choices:
        return False, None

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return False, None

    content = message.get("content")
    if content is None:
        return False, None

    if isinstance(content, dict):
        return _action_from_payload(content)

    if isinstance(content, str):
        inner = _parse_json(content.strip())
        if inner is not None:
            return _action_from_payload(inner)

    return False, None


def is_valid_action_payload(response_text: str) -> bool:
    valid, _ = extract_action_from_llm_response(response_text)
    return valid
