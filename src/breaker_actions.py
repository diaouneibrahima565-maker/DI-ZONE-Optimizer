from uuid import uuid4
from copy import deepcopy

ALLOWED_ACTIONS = {"memory_write"}

class BreakerActionError(Exception):
    pass

def create_action_proposal(action_type, action_data):
    if not isinstance(action_type, str) or not action_type.strip():
        raise BreakerActionError("Syntax Error. The action type was invalid.")

    action_type = action_type.strip()

    if action_type not in ALLOWED_ACTIONS:
        raise BreakerActionError("Action type is not allowed.")

    if not isinstance(action_data, dict):
        raise BreakerActionError("There are no data stored for actions.")

    if set(action_data.keys()) != {"content"}:
        raise BreakerActionError("Invalid action data fields.")

    content = action_data["content"]

    if not isinstance(content, str):
        raise BreakerActionError("Memory content must be text.")

    content = content.strip()

    if not content:
        raise BreakerActionError("Memory content cannot be empty.")

    copied_data = deepcopy(action_data)

    copied_data["content"] = content

    action_id = uuid4().hex

    proposal = {
        "action_id": action_id,
        "action_type": action_type,
        "action_data": copied_data,
        "status": "pending_approval"
    }

    return proposal

