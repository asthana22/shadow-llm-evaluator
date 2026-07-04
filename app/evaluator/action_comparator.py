def actions_match(primary_action: str | None, candidate_action: str | None) -> bool:
    if primary_action is None or candidate_action is None:
        return False
    return primary_action == candidate_action
