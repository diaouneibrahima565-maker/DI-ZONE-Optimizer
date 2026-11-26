import time
import unittest
import tkinter as tk
import customtkinter as ctk

from unittest.mock import Mock

from breaker_controller import BreakerController
from breaker_hud import BreakerHUD


class TestBreakerHUDControls(unittest.TestCase):

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

    def enter_text(self, content):
        self.hud.memory_entry.delete(0, "end")
        self.hud.memory_entry.insert(0, content)

    def test_01_controls_exist(self):
        self.assertIsInstance(
            self.hud.memory_entry,
            ctk.CTkEntry
        )
        self.assertIsInstance(
            self.hud.preview_button,
            ctk.CTkButton
        )
        self.assertIsInstance(
            self.hud.approve_button,
            ctk.CTkButton
        )
        self.assertIsInstance(
            self.hud.cancel_button,
            ctk.CTkButton
        )

    def test_02_approval_initially_disabled(self):
        self.assertEqual(
            self.hud.approve_button.cget("state"),
            "disabled"
        )
        self.assertEqual(
            self.hud.cancel_button.cget("state"),
            "disabled"
        )

        self.writer.assert_not_called()

    def test_03_preview_does_not_execute(self):
        self.enter_text("Learn Python")
        self.hud.preview_button.invoke()

        self.assertIsNotNone(
            self.hud._pending_action_id
        )

        self.assertEqual(
            self.hud.approve_button.cget("state"),
            "normal"
        )

        self.assertIn(
            "Learn Python",
            self.hud.memory_preview_label.cget("text")
        )

        self.writer.assert_not_called()

    def test_04_approve_executes_once(self):
        self.enter_text("Learn Python")

        self.hud.preview_button.invoke()
        self.hud.approve_button.invoke()
        self.wait_for_hud("completed")

        self.writer.assert_called_once_with(
            "Learn Python"
        )

        self.assertIsNone(
            self.hud._pending_action_id
        )

        self.assertIn(
            "DEMO",
            self.hud.system_status_label.cget("text")
        )

    def test_05_cancel_prevents_execution(self):
        self.enter_text("Learn Python")

        self.hud.preview_button.invoke()
        action_id = self.hud._pending_action_id

        self.hud.cancel_button.invoke()

        self.writer.assert_not_called()

        events = [
            event["event"]
            for event in self.controller.get_history(action_id)
        ]

        self.assertEqual(
            events,
            ["proposed", "canceled"]
        )

    def test_06_invalid_content_rejected(self):
        self.enter_text("   ")
        self.hud.preview_button.invoke()

        self.assertIsNone(
            self.hud._pending_action_id
        )

        self.writer.assert_not_called()

        self.assertEqual(
            self.hud.approve_button.cget("state"),
            "disabled"
        )

    def test_07_duplicate_preview_blocked(self):
        self.enter_text("First memory")
        self.hud.preview_button.invoke()

        first_id = self.hud._pending_action_id

        self.enter_text("Second memory")
        self.hud.preview_button.invoke()

        self.assertEqual(
            self.hud._pending_action_id,
            first_id
        )

        self.assertEqual(
            len(self.controller.get_history()),
            1
        )

    def test_08_failed_writer_not_reported_as_success(self):
        self.writer.side_effect = OSError(
            "Simulated storage failure"
        )

        self.enter_text("Test memory")
        self.hud.preview_button.invoke()
        self.hud.approve_button.invoke()
        self.wait_for_hud("error")

        self.writer.assert_called_once()

        self.assertIsNone(
            self.hud._pending_action_id
        )

        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "MEMORY WRITE FAILED"
        )

    def test_09_no_controller_disables_preview(self):
        separate_hud = BreakerHUD(self.root)

        try:
            self.assertEqual(
                separate_hud.preview_button.cget("state"),
                "disabled"
            )
        finally:
            separate_hud.destroy()


    def wait_for_hud(self, expected_state, timeout=3):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            self.root.update()

            if (
                self.hud._reactor_state == expected_state
                and self.hud._active_action_id is None
            ):
                return

            time.sleep(0.01)

        self.fail(
            f"HUD did not reach {expected_state!r} "
            f"within {timeout} seconds"
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
