from copy import deepcopy
from uuid import uuid4
from datetime import datetime, timezone

from breaker_approval import ActionApprovalManager
from breaker_execution import MemoryActionExecutor, BreakerExecutionError

class BreakerWorkflow:

    def __init__(self, memory_writer):
        self._manager = ActionApprovalManager()
        self._executor = MemoryActionExecutor(self._manager, memory_writer)
        self._events = []

    def _record_event(self, action_id, event):
        event_id = uuid4().hex

        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "event_id": event_id,
            "action_id": action_id,
            "event": event,
            "timestamp": timestamp
        }

        self._events.append(record)

    def propose(self, action_type, action_data):
        proposal = self._manager.propose(action_type, action_data)

        action_id = proposal["action_id"]

        self._record_event(action_id, "proposed")

        return proposal

    def approve(self, action_id):
        approved_proposal = self._manager.approve(action_id)

        self._record_event(action_id, "approved")

        return approved_proposal

    def cancel(self, action_id):
        canceled_proposal = self._manager.cancel(action_id)

        self._record_event(action_id, "canceled")

        return canceled_proposal

    def execute(self, action_id):
        self._record_event(action_id, "execution_requested")

        try:
            result = self._executor.execute(action_id)

        except BreakerExecutionError:
            self._record_event(action_id, "failed")
            raise

        self._record_event(action_id, "completed")

        return result

    def get_history(self, action_id=None):
        if action_id is None:
            return deepcopy(self._events)

        else:
            matching_events = []

        for record in self._events:
            if record["action_id"] == action_id:
                matching_events.append(record)

        return deepcopy(matching_events)