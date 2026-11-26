
import threading
import time
import tkinter as tk
import unittest

import customtkinter as ctk

from unittest.mock import Mock

from breaker_controller import BreakerController
from breaker_hud import BreakerHUD
from breaker_worker import BreakerActionWorker


class TestBreakerHUDWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(
                f"Graphical display unavailable: {error}"
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
        self.hud.destroy()
        self.root.update_idletasks()

    def enter_memory(self, content):
        self.hud.memory_entry.delete(0, "end")
        self.hud.memory_entry.insert(0, content)

    def pump_until(self, condition, timeout=3):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            self.root.update()

            if condition():
                return

            time.sleep(0.01)

        self.fail("Timed out waiting for HUD condition")

    def test_01_worker_is_initialized(self):
        self.assertIsInstance(
            self.hud._worker,
            BreakerActionWorker
        )

        self.assertIsNone(
            self.hud._active_action_id
        )

        self.assertIsNotNone(
            self.hud._worker_poll_after_id
        )

        self.writer.assert_not_called()

    def test_02_approval_starts_worker(self):
        self.enter_memory("Learn concurrent Python")

        self.hud._preview_memory()
        action_id = self.hud._pending_action_id

        self.hud._approve_memory()

        self.assertEqual(
            self.hud._active_action_id,
            action_id
        )

        self.assertEqual(
            self.hud._reactor_state,
            "executing"
        )

        self.assertEqual(
            self.hud.approve_button.cget("state"),
            "disabled"
        )

        self.pump_until(
            lambda: self.hud._active_action_id is None
        )

    def test_03_completed_action_updates_hud(self):
        self.enter_memory("Practice threading")

        self.hud._preview_memory()
        self.hud._approve_memory()

        self.pump_until(
            lambda: self.hud._reactor_state == "completed"
        )

        self.writer.assert_called_once_with(
            "Practice threading"
        )

        self.assertIsNone(
            self.hud._pending_action_id
        )

        self.assertIsNone(
            self.hud._active_action_id
        )

        self.assertEqual(
            self.hud.preview_button.cget("state"),
            "normal"
        )

        self.assertIn(
            "DEMO",
            self.hud.system_status_label.cget("text")
        )

    def test_04_failed_writer_updates_hud(self):
        self.writer.side_effect = OSError(
            "Simulated storage failure"
        )

        self.enter_memory("Failure test")

        self.hud._preview_memory()
        self.hud._approve_memory()

        self.pump_until(
            lambda: self.hud._reactor_state == "error"
        )

        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "MEMORY WRITE FAILED"
        )

        self.assertIsNone(
            self.hud._active_action_id
        )

        self.writer.assert_called_once()

    def test_05_cancel_still_prevents_execution(self):
        self.enter_memory("Do not save this")

        self.hud._preview_memory()
        self.hud._cancel_memory()

        self.assertEqual(
            self.hud._reactor_state,
            "canceled"
        )

        self.assertIsNone(
            self.hud._active_action_id
        )

        self.writer.assert_not_called()

    def test_06_unrelated_event_is_ignored(self):
        self.hud._worker.results.put({
            "action_id": "unrelated-action",
            "status": "completed",
            "success": True
        })

        self.pump_until(
            lambda: self.hud._worker.results.empty()
        )

        self.assertEqual(
            self.hud._reactor_state,
            "standby"
        )

        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "HUD READY"
        )

        self.writer.assert_not_called()

    def test_07_reactor_animates_while_worker_runs(self):
        started = threading.Event()
        release = threading.Event()

        def slow_writer(content):
            started.set()
            release.wait(timeout=2)
            return True

        self.writer.side_effect = slow_writer

        self.enter_memory("Hold until release")

        self.hud._preview_memory()
        self.hud._approve_memory()

        try:
            self.assertTrue(
                started.wait(timeout=1)
            )

            self.assertEqual(
                self.hud._reactor_state,
                "executing"
            )

            previous_frame = self.hud._animation_frame

            self.pump_until(
                lambda: (
                    self.hud._animation_frame
                    > previous_frame + 1
                )
            )

            self.assertEqual(
                self.hud._reactor_state,
                "executing"
            )

            # A second approval must not start a new write.
            self.hud._approve_memory()

        finally:
            release.set()

            if self.hud._worker._thread is not None:
                self.hud._worker._thread.join(timeout=2)

        self.pump_until(
            lambda: self.hud._reactor_state == "completed"
        )

        self.writer.assert_called_once_with(
            "Hold until release"
        )

    def test_08_no_controller_has_no_worker(self):
        separate_hud = BreakerHUD(self.root)

        try:
            self.assertIsNone(
                separate_hud._worker
            )

            self.assertEqual(
                separate_hud.preview_button.cget("state"),
                "disabled"
            )

            self.assertIsNone(
                separate_hud._worker_poll_after_id
            )

        finally:
            separate_hud.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
