from breaker_approval import ActionApprovalError, ActionApprovalManager

class BreakerExecutionError(Exception):
    pass

class MemoryActionExecutor:
    def __init__(self, approval_manager, memory_writer):
        if not isinstance(approval_manager, ActionApprovalManager):
            raise BreakerExecutionError("Approval not managed by Action Approval Manager.")

        if not callable(memory_writer):
            raise BreakerExecutionError("Memory writer must be callable.")

        self._approval_manager = approval_manager

        self._memory_writer = memory_writer

        self._attempts = {}

    def execute(self, action_id):
        if not isinstance(action_id, str):
            raise BreakerExecutionError("Action should be a text.")

        if not action_id.strip():
            raise BreakerExecutionError("Action does not exist.")

        try:
            proposal = self._approval_manager.get_proposal(action_id)

        except ActionApprovalError as error:
            raise BreakerExecutionError("Action was not found.") from error

        current_status = proposal["status"]

        if current_status != "approved":
            raise BreakerExecutionError("Action has not been approved.")

        if proposal["action_type"] != "memory_write":
            raise BreakerExecutionError("Action typr should be the same as memory write.")

        if not isinstance(proposal["action_data"], dict):
            raise BreakerExecutionError("Action data should be a dictionary.")

        content = proposal["action_data"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise BreakerExecutionError("Invalid Syntax. Make sure that the content is exactly written.")

        if action_id in self._attempts:
            raise BreakerExecutionError("Action execution already attempted.")

        self._attempts[action_id] = "started"

        try:
            confirmed = self._memory_writer(content)

        except Exception as error:
            self._attempts[action_id] = "failed"

            raise BreakerExecutionError("Memory write failed.") from error

        if confirmed is not True:
            self._attempts[action_id] = "failed"

            raise BreakerExecutionError("Memory write was not confirmed.")

        self._attempts[action_id] = "completed"

        execution_result = {
            "action_id": action_id,
            "action_type": "memory_write",
            "status": "completed"
        }
        return execution_result