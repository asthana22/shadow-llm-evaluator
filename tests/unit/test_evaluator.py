import pytest

from app.evaluator import evaluate_responses
from app.evaluator.json_validator import extract_action_from_llm_response, is_valid_action_payload


PRIMARY = '{"choices":[{"message":{"content":"{\\"action\\": \\"search\\"}"}}]}'
CANDIDATE_MATCH = '{"choices":[{"message":{"content":"{\\"action\\": \\"search\\"}"}}]}'
CANDIDATE_MISMATCH = '{"choices":[{"message":{"content":"{\\"action\\": \\"browse\\"}"}}]}'
INVALID = "not json"


def test_extract_action_from_chat_completion():
    valid, action = extract_action_from_llm_response(PRIMARY)
    assert valid is True
    assert action == "search"


def test_extract_action_flat_json():
    valid, action = extract_action_from_llm_response('{"action": "book"}')
    assert valid is True
    assert action == "book"


def test_invalid_payload():
    assert is_valid_action_payload(INVALID) is False
    assert is_valid_action_payload('{"choices":[]}') is False


def test_evaluate_exact_match():
    result = evaluate_responses(PRIMARY, CANDIDATE_MATCH)
    assert result.primary_valid is True
    assert result.candidate_valid is True
    assert result.exact_action_match is True


def test_evaluate_mismatch():
    result = evaluate_responses(PRIMARY, CANDIDATE_MISMATCH)
    assert result.primary_valid is True
    assert result.candidate_valid is True
    assert result.exact_action_match is False


def test_evaluate_invalid_candidate():
    result = evaluate_responses(PRIMARY, INVALID)
    assert result.primary_valid is True
    assert result.candidate_valid is False
    assert result.exact_action_match is False
