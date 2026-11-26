
import threading
import tkinter as tk
import unittest

from types import SimpleNamespace
from unittest.mock import Mock

import customtkinter as ctk

from breaker_approval import ActionApprovalError
from breaker_controller import BreakerController
from breaker_hud import BreakerHUD


class TestBreakerHUDShutdown(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(
                f"Display unavailable: {error}"
            )

        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root"):
            cls.root.destroy()

    def setUp(self):
        self.writer = Mock(return_value=True)
        self.controller = BreakerController(self.writer)

        self.hud = BreakerHUD(
            self.root,
            controller=self.controller,
            demo_mode=True
        )

        self.hud.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        if self.hud.winfo_exists():
            self.hud.destroy()

        worker = self.hud._worker

        if worker is not None:
            thread = worker._thread

            if thread is not None and thread.is_alive():
                thread.join(timeout=3)

    def enter_memory(self, content):
        self.hud.memory_entry.delete(0, "end")
        self.hud.memory_entry.insert(0, content)

    def test_01_idle_shutdown_stops_callbacks(self):
        worker = self.hud._worker

        self.assertIsNotNone(
            self.hud._animation_after_id
        )

        self.assertIsNotNone(
            self.hud._worker_poll_after_id
        )

        self.hud.destroy()

        self.assertIs(worker._closed, True)
        self.assertIs(self.hud._cleanup_done, True)
        self.assertIs(self.hud._animation_stopped, True)

        self.assertIsNone(
            self.hud._animation_after_id
        )

        self.assertIsNone(
            self.hud._worker_poll_after_id
        )

        with self.assertRaises(RuntimeError):
            worker.start("another-action")

    def test_02_shutdown_cancels_pending_proposal(self):
        self.enter_memory("Remember this test")

        self.hud._preview_memory()
        action_id = self.hud._pending_action_id

        self.assertIsNotNone(action_id)

        self.hud.destroy()

        events = [
            event["event"]
            for event in self.controller.get_history(action_id)
        ]

        self.assertEqual(
            events,
            ["proposed", "canceled"]
        )

        self.writer.assert_not_called()

        self.assertIsNone(
            self.hud._pending_action_id
        )

        self.assertIs(
            self.hud._worker._closed,
            True
        )

    def test_03_running_action_finishes_after_shutdown(self):
        started = threading.Event()
        release = threading.Event()

        def slow_writer(content):
            started.set()

            if not release.wait(timeout=3):
                return False

            return True

        self.writer.side_effect = slow_writer

        self.enter_memory("Approved before closing")

        self.hud._preview_memory()
        action_id = self.hud._pending_action_id

        self.hud._approve_memory()

        worker = self.hud._worker

        try:
            self.assertTrue(
                started.wait(timeout=2)
            )

            self.assertEqual(
                self.hud._active_action_id,
                action_id
            )

            self.hud.destroy()

            self.assertIs(worker._closed, True)

            events_before_completion = [
                item["event"]
                for item in self.controller.get_history(action_id)
            ]

            self.assertNotIn(
                "canceled",
                events_before_completion
            )

        finally:
            release.set()

            if worker._thread is not None:
                worker._thread.join(timeout=3)

        self.assertFalse(
            worker._thread.is_alive()
        )

        result = worker.results.get(timeout=2)

        self.assertEqual(
            result["action_id"],
            action_id
        )

        self.assertEqual(
            result["status"],
            "completed"
        )

        self.assertIs(result["success"], True)

        self.writer.assert_called_once_with(
            "Approved before closing"
        )

        events = [
            item["event"]
            for item in self.controller.get_history(action_id)
        ]

        self.assertIn("completed", events)
        self.assertNotIn("canceled", events)

    def test_04_cleanup_is_idempotent(self):
        self.enter_memory("Cancel exactly once")

        self.hud._preview_memory()
        action_id = self.hud._pending_action_id

        original_cancel = self.controller.cancel_action

        self.controller.cancel_action = Mock(
            wraps=original_cancel
        )

        destroy_event = SimpleNamespace(
            widget=self.hud
        )

        self.hud._on_destroy(destroy_event)
        self.hud._on_destroy(destroy_event)

        self.hud.destroy()

        self.controller.cancel_action.assert_called_once_with(
            action_id
        )

        self.assertIs(
            self.hud._cleanup_done,
            True
        )

    def test_05_child_destroy_event_is_ignored(self):
        child_event = SimpleNamespace(
            widget=self.hud.memory_entry
        )

        self.hud._on_destroy(child_event)

        self.assertIs(
            self.hud._cleanup_done,
            False
        )

        self.assertIs(
            self.hud._worker._closed,
            False
        )

        self.assertIs(
            self.hud._animation_stopped,
            False
        )

        self.assertIsNotNone(
            self.hud._worker_poll_after_id
        )

    def test_06_cancellation_error_does_not_block_shutdown(self):
        self.enter_memory("Test failed cancellation")

        self.hud._preview_memory()
        action_id = self.hud._pending_action_id

        self.controller.cancel_action = Mock(
            side_effect=ActionApprovalError(
                "Simulated cancellation failure"
            )
        )

        self.hud.destroy()

        self.controller.cancel_action.assert_called_once_with(
            action_id
        )

        self.assertIs(
            self.hud._worker._closed,
            True
        )

        self.assertIs(
            self.hud._cleanup_done,
            True
        )

        # Cancellation was not confirmed.
        self.assertEqual(
            self.hud._pending_action_id,
            action_id
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
