
import customtkinter as ctk

from breaker_hud import BreakerHUD
from breaker_controller import BreakerController


def demo_memory_writer(content):
    # Simulate a memory write without saving anything.
    print("SIMULATED MEMORY WRITE:", content)
    return True


def main():
    ctk.set_appearance_mode("dark")

    app = ctk.CTk()
    app.title("DI-ZONE Optimizer — Breaker Preview")
    app.geometry("1100x650")
    app.minsize(800, 500)

    # Connect our simulated writer to the controller.
    controller = BreakerController(demo_memory_writer)

    # Give the controller to the HUD.
    hud = BreakerHUD(
        app,
        controller=controller,
        demo_mode=True
    )

    hud.pack(fill="both", expand=True)

    app.mainloop()


if __name__ == "__main__":
    main()
