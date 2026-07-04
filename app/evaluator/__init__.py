from app.evaluator.action_comparator import actions_match
from app.evaluator.json_validator import extract_action_from_llm_response
from app.types.evaluation import EvaluationResult


def evaluate_responses(primary_response: str, candidate_response: str) -> EvaluationResult:
    primary_valid, primary_action = extract_action_from_llm_response(primary_response)
    candidate_valid, candidate_action = extract_action_from_llm_response(candidate_response)

    return EvaluationResult(
        primary_valid=primary_valid,
        candidate_valid=candidate_valid,
        exact_action_match=actions_match(primary_action, candidate_action),
        primary_action=primary_action,
        candidate_action=candidate_action,
    )
