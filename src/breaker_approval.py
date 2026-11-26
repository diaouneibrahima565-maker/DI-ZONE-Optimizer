from copy import deepcopy
from breaker_actions import create_action_proposal

class ActionApprovalError(Exception):
    pass

class ActionApprovalManager:

    def __init__(self):
        self._proposals = {}

    def propose(self, action_type, action_data):
        proposal = create_action_proposal(action_type, action_data)

        action_id = proposal["action_id"]

        self._proposals[action_id] = deepcopy(proposal)

        return deepcopy(proposal)

    def _find_proposal(self, action_id):
        if not isinstance(action_id, str):
            raise ActionApprovalError("This action does not exist. Action ID should be a string.")

        if not action_id.strip():
            raise ActionApprovalError("Invalid Syntax. There are no actions.")

        if action_id not in self._proposals:
            raise ActionApprovalError("Action not found.")

        proposal = self._proposals[action_id]
        return proposal

    def get_proposal(self, action_id):
        proposal = self._find_proposal(action_id)

        return deepcopy(proposal)

    def approve(self, action_id):
        proposal = self._find_proposal(action_id)

        current_status = proposal["status"]

        if current_status != "pending_approval":
            raise ActionApprovalError("Action cannot be approved.")

        proposal["status"] = "approved"

        return deepcopy(proposal)

    def cancel(self, action_id):
        proposal = self._find_proposal(action_id)

        current_status = proposal["status"]

        if current_status != "pending_approval":
            raise ActionApprovalError("Action cannot be canceled.")

        proposal["status"] = "canceled"

        return deepcopy(proposal)