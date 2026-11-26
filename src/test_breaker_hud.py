
import unittest
import tkinter as tk
import customtkinter as ctk

from breaker_hud import BreakerHUD


class TestBreakerHUD(unittest.TestCase):

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
        self.hud = BreakerHUD(self.root)
        self.hud.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        if self.hud is not None:
            self.hud.destroy()

    def test_01_hud_is_customtkinter_frame(self):
        self.assertIsInstance(
            self.hud,
            ctk.CTkFrame
        )

    def test_02_layout_panels_exist(self):
        self.assertIsInstance(
            self.hud.sidebar,
            ctk.CTkFrame
        )

        self.assertIsInstance(
            self.hud.center_panel,
            ctk.CTkFrame
        )

        self.assertIsInstance(
            self.hud.right_panel,
            ctk.CTkFrame
        )

    def test_03_reactor_canvas_exists(self):
        self.assertIsInstance(
            self.hud.core_canvas,
            tk.Canvas
        )

    def test_04_initial_system_status(self):
        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "HUD READY"
        )

    def test_05_microphone_is_off(self):
        self.assertEqual(
            self.hud.microphone_status_label.cget("text"),
            "MICROPHONE OFF"
        )

    def test_06_update_system_status(self):
        self.hud.set_system_status("PROCESSING")

        self.assertEqual(
            self.hud.system_status_label.cget("text"),
            "PROCESSING"
        )

    def test_07_animation_updates_canvas_items(self):
        ring_id = self.hud._ring_segments[0][0]
        initial_start = float(self.hud.core_canvas.itemcget(ring_id, "start"))
        initial_glow = self.hud.core_canvas.itemcget(
            self.hud.core_glow_id, "outline"
        )
        initial_frame = self.hud._animation_frame

        self.root.after(100, self.root.quit)
        self.root.mainloop()

        self.assertGreater(self.hud._animation_frame, initial_frame)
        self.assertNotEqual(
            float(self.hud.core_canvas.itemcget(ring_id, "start")),
            initial_start
        )
        self.assertNotEqual(
            self.hud.core_canvas.itemcget(self.hud.core_glow_id, "outline"),
            initial_glow
        )
        self.assertEqual(
            self.hud.core_canvas.itemcget(self.hud.core_text_id, "text"),
            "BREAKER"
        )

    def test_08_destroy_stops_animation_callback(self):
        hud = self.hud
        callback_id = hud._animation_after_id
        self.assertIsNotNone(callback_id)
        self.assertTrue(self.root.tk.call("after", "info", callback_id))

        hud.destroy()
        self.hud = None

        self.assertTrue(hud._animation_stopped)
        self.assertIsNone(hud._animation_after_id)
        with self.assertRaises(tk.TclError):
            self.root.tk.call("after", "info", callback_id)

        for _ in range(3):
            repeated_hud = BreakerHUD(self.root)
            repeated_callback_id = repeated_hud._animation_after_id
            repeated_hud.destroy()

            self.assertTrue(repeated_hud._animation_stopped)
            self.assertIsNone(repeated_hud._animation_after_id)
            with self.assertRaises(tk.TclError):
                self.root.tk.call("after", "info", repeated_callback_id)

    def test_09_reactor_scales_and_stays_centered_at_preview_sizes(self):
        outer_track_id = self.hud._track_rings[0][0]
        self.root.deiconify()
        try:
            for geometry in ("1100x650", "800x500"):
                self.root.geometry(geometry)
                self.root.update()

                canvas_width = self.hud.core_canvas.winfo_width()
                canvas_height = self.hud.core_canvas.winfo_height()
                x1, y1, x2, y2 = self.hud.core_canvas.coords(outer_track_id)
                diameter = x2 - x1

                self.assertAlmostEqual((x1 + x2) / 2, canvas_width / 2, delta = 1)
                self.assertAlmostEqual((y1 + y2) / 2, canvas_height / 2, delta = 1)
                self.assertAlmostEqual(
                    diameter / min(canvas_width, canvas_height),
                    0.8712,
                    delta = 0.02
                )
        finally:
            self.root.withdraw()


if __name__ == "__main__":
    unittest.main(verbosity=2)
