REQUEST_IDLE = "idle"
REQUEST_GENERATING = "generating"
REQUEST_CLOSED = "closed"

class RequestLifecycleError(Exception):
    pass

class RequestLifecycle:

    def __init__(self):
        self.state = REQUEST_IDLE
        self.active_request = None

    def start(
            self, request_id,
            folder_id, conversation_id
    ):
        if self.state == REQUEST_CLOSED:
            raise RequestLifecycleError("The request lifecycle is closed.")

        if self.state == REQUEST_GENERATING:
            raise RequestLifecycleError("An AI request is already active.")

        for identifier in (request_id, folder_id, conversation_id):
            if not isinstance(identifier, str) or not identifier.strip():
                raise RequestLifecycleError("Invalid request identifier.")

        self.active_request = {"request_id": request_id,
                              "folder_id": folder_id,
                              "conversation_id": conversation_id,}
        self.state = REQUEST_GENERATING

        return self.active_request.copy()

    def matches(self, request_id):
        if self.state != REQUEST_GENERATING:
            return False

        return self.active_request["request_id"] == request_id

    def finish(self, request_id):
        if self.matches(request_id) is False:
            return False

        self.active_request = None
        self.state = REQUEST_IDLE

        return True

    def close(self):
        self.active_request = None
        self.state = REQUEST_CLOSED
        