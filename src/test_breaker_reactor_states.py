import time
import unittest
import tkinter as tk
import customtkinter as ctk

from unittest.mock import Mock

from breaker_controller import BreakerController
from breaker_hud import BreakerHUD, REACTOR_PROFILES


class TestBreakerReactorStates(unittest.TestCase):

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

    def enter_memory(self, content):
        self.hud.memory_entry.delete(0, "end")
        self.hud.memory_entry.insert(0, content)

    def test_01_starts_in_standby(self):
        self.assertEqual(
            self.hud._reactor_state,
            "standby"
        )

    def test_02_accepts_valid_states(self):
        for state in REACTOR_PROFILES:
            with self.subTest(state=state):
                self.hud._set_reactor_state(state)

                self.assertEqual(
                    self.hud._reactor_state,
                    state
                )

    def test_03_rejects_unknown_state(self):
        with self.assertRaises(ValueError):
            self.hud._set_reactor_state(
                "unknown_state"
            )

        self.assertEqual(
            self.hud._reactor_state,
            "standby"
        )

    def test_04_animation_speed_changes(self):
        self.hud._set_reactor_state("standby")

        before = self.hud._animation_phase
        self.hud._update_animation()
        standby_change = (
            self.hud._animation_phase - before
        )

        self.hud._set_reactor_state("executing")

        before = self.hud._animation_phase
        self.hud._update_animation()
        executing_change = (
            self.hud._animation_phase - before
        )

        self.assertAlmostEqual(
            standby_change,
            1.0
        )

        self.assertAlmostEqual(
            executing_change,
            2.0
        )

    def test_05_preview_changes_state(self):
        self.enter_memory("Learn Python")

        self.hud._preview_memory()

        self.assertEqual(
            self.hud._reactor_state,
            "awaiting_approval"
        )

        self.writer.assert_not_called()

    def test_06_cancel_changes_state(self):
        self.enter_memory("Learn Python")

        self.hud._preview_memory()
        self.hud._cancel_memory()

        self.assertEqual(
            self.hud._reactor_state,
            "canceled"
        )

        self.writer.assert_not_called()

    def test_07_approved_action_completes(self):
        self.enter_memory("Learn Python")

        self.hud._preview_memory()
        self.hud._approve_memory()
        self.wait_for_hud("completed")

        self.assertEqual(
            self.hud._reactor_state,
            "completed"
        )

        self.writer.assert_called_once_with(
            "Learn Python"
        )

    def test_08_failed_action_changes_state(self):
        self.writer.side_effect = OSError(
            "Simulated disk failure"
        )

        self.enter_memory("Learn Python")

        self.hud._preview_memory()
        self.hud._approve_memory()
        self.wait_for_hud("error")

        self.assertEqual(
            self.hud._reactor_state,
            "error"
        )

        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "MEMORY WRITE FAILED"
        )

    def test_09_state_change_preserves_phase(self):
        self.hud._update_animation()

        previous_phase = (
            self.hud._animation_phase
        )

        self.hud._set_reactor_state(
            "awaiting_approval"
        )

        self.assertEqual(
            self.hud._animation_phase,
            previous_phase
        )


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
