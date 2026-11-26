from breaker_workflow import BreakerWorkflow

class BreakerController:

    def __init__(self, memory_writer):
        self._workflow = BreakerWorkflow(memory_writer)

    def submit_memory(self, content):
        proposal = self._workflow.propose(
            "memory_write",
            {"content": content}
        )

        return proposal

    def approve_and_execute(self, action_id):
        self._workflow.approve(action_id)
        result = self._workflow.execute(action_id)
        return result

    def cancel_action(self, action_id):
        canceled_proposal = self._workflow.cancel(action_id)

        return canceled_proposal

    def get_history(self, action_id=None):
        return self._workflow.get_history(action_id)
