import threading
import queue

class BreakerActionWorker:

    def __init__(self, controller):
        self._controller = controller
        self.results = queue.Queue()
        self._thread = None
        self._closed = False
        self._lifecycle_lock = threading.Lock()

    def start(self, action_id):
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("Invalid action ID.")

        with self._lifecycle_lock:
            if self._closed is True:
                raise RuntimeError("Worker is shut down.")

            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("An action is already running.")

            self._thread = threading.Thread(target = self._run, args = (action_id,), daemon = False)

            self._thread.start()

    def _run(self, action_id):
        try:
            result = self._controller.approve_and_execute(action_id)

            success = (isinstance(result, dict) and result.get("status") == "completed")

            event = {
                "action_id": action_id,
                "status": "completed" if success else "failed",
                "success": success
            }

        except Exception as error:
            error_type = type(error).__name__

            event = {
                "action_id": action_id,
                "status": "failed",
                "success": False,
                "error_type": error_type
            }

        self.results.put(event)

    def shutdown(self):
        with self._lifecycle_lock:
            self._closed = True