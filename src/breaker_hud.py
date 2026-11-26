
import math
import tkinter as tk
import customtkinter as ctk
import queue

from breaker_actions import BreakerActionError
from breaker_approval import ActionApprovalError
from breaker_worker import BreakerActionWorker
from ui_text import create_read_only_textbox, set_read_only_text


# ============================================================
# BREAKER THEME
# ============================================================

BG_COLOR = "#090F0B"
PANEL_COLOR = "#142019"
SURFACE_COLOR = "#101A14"

NEON_GREEN = "#4EF294"
MEDIUM_GREEN = "#2B9C62"
BORDER_GREEN = "#275638"

TEXT_COLOR = "#B8CEC0"
MUTED_TEXT = "#8FA99A"

AWAITING_COLOR = "#E6C06C" #waiting for approval
EXECUTING_COLOR = "#72FFAF" #performing an action
ERROR_COLOR = "#E6A078" #failure or error

REACTOR_PROFILES = {
    "standby":{
        "speed": 1.0,
        "color": NEON_GREEN
    },
    "awaiting_approval": {
        "speed": 0.45,
        "color": AWAITING_COLOR
    },
    "executing": {
        "speed": 2.0,
        "color": EXECUTING_COLOR
    },
    "completed": {
        "speed": 0.75,
        "color": NEON_GREEN
    },
    "canceled": {
        "speed": 0.55,
        "color": MUTED_TEXT
    },
    "error": {
        "speed": 0.1,
        "color": ERROR_COLOR
    }
}


class BreakerHUD(ctk.CTkFrame):

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self, master, controller=None, demo_mode=False, on_back=None):
        super().__init__(
            master,
            fg_color=BG_COLOR,
            corner_radius=0
        )

        self._controller = controller
        self._demo_mode = demo_mode
        self._on_back = on_back
        self._pending_action_id = None

        if controller is not None:
            self._worker = BreakerActionWorker(controller)

        else:
            self._worker = None

        self._active_action_id = None
        self._worker_poll_after_id = None

        # Animation state
        self._animation_after_id = None
        self._animation_stopped = False
        self._animation_frame = 0

        self._cleanup_done = False

        # Reactor state
        self._reactor_state = "standby"
        self._animation_phase = 0.0

        # Main grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # Main panels
        self.sidebar = ctk.CTkFrame(
            self,
            width=190,
            fg_color=PANEL_COLOR,
            corner_radius=8
        )

        self.center_panel = ctk.CTkFrame(
            self,
            fg_color=BG_COLOR,
            corner_radius=0
        )

        self.right_panel = ctk.CTkFrame(
            self,
            width=220,
            fg_color=PANEL_COLOR,
            corner_radius=8
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(10, 5),
            pady=10
        )

        self.center_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=5,
            pady=10
        )

        self.right_panel.grid(
            row=0,
            column=2,
            sticky="nsew",
            padx=(5, 10),
            pady=10
        )

        # Build interface
        self._build_sidebar()
        self._build_center()
        self._build_status()
        self._build_memory_controls()

        # Start animation
        tk.Misc.bind(
            self,
            "<Destroy>",
            self._on_destroy,
            add="+"
        )

        self._schedule_animation()

        if self._worker is not None:
            self._schedule_worker_poll()

    # ========================================================
    # SIDEBAR
    # ========================================================

    def _build_sidebar(self):

        title_label = ctk.CTkLabel(
            self.sidebar,
            text="BREAKER",
            text_color=NEON_GREEN,
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        )

        title_label.pack(
            pady=(25, 35),
            padx=15
        )

        if self._on_back is not None:
            back_button = ctk.CTkButton(
                self.sidebar,
                text="← Back to Optimizer",
                command=self._on_back,
                fg_color=SURFACE_COLOR,
                hover_color=BORDER_GREEN,
                text_color=TEXT_COLOR,
                anchor="w",
            )
            back_button.pack(fill="x", padx=12, pady=(0, 20))

        navigation_items = [
            "WORK MODE",
            "APPROVED MEMORY ACTIONS",
        ]

        for item in navigation_items:

            navigation_label = ctk.CTkLabel(
                self.sidebar,
                text=item,
                text_color=TEXT_COLOR,
                font=ctk.CTkFont(size=14),
                anchor="w"
            )

            navigation_label.pack(
                fill="x",
                padx=18,
                pady=10
            )

    # ========================================================
    # CENTER PANEL AND REACTOR
    # ========================================================

    def _build_center(self):

        self.center_panel.grid_columnconfigure(
            0,
            weight=1
        )

        self.center_panel.grid_rowconfigure(
            1,
            weight=3
        )

        self.center_panel.grid_rowconfigure(
            2,
            weight=1,
            minsize=175
        )

        header_label = ctk.CTkLabel(
            self.center_panel,
            text="DI-ZONE OPTIMIZER",
            text_color=MUTED_TEXT,
            font=ctk.CTkFont(size=14)
        )

        header_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(12, 4)
        )

        # Reactor container
        self.reactor_container = ctk.CTkFrame(
            self.center_panel,
            fg_color=BG_COLOR,
            corner_radius=0
        )

        self.reactor_container.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        self.reactor_container.grid_columnconfigure(
            0,
            weight=1
        )

        self.reactor_container.grid_rowconfigure(
            0,
            weight=1
        )

        # Responsive Canvas
        self.core_canvas = tk.Canvas(
            self.reactor_container,
            width=1,
            height=1,
            bg=BG_COLOR,
            borderwidth=0,
            highlightthickness=0
        )

        self.core_canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # Reactor collections
        self._ring_segments = []
        self._track_rings = []
        self._tick_items = []
        self._scanner_items = []
        self._indicator_items = []

        self._last_reactor_size = None

        self._reactor_center_x = 125
        self._reactor_center_y = 125
        self._reactor_radius = 120
        self._reactor_scale = 1

        # Static circular tracks
        for radius_fraction, width_scale in (
            (0.99, 0.7),
            (0.90, 1.0),
            (0.79, 0.7),
            (0.68, 0.6),
            (0.57, 0.7),
            (0.47, 0.6),
            (0.38, 1.0)
        ):

            item_id = self.core_canvas.create_oval(
                0, 0, 1, 1,
                outline=BORDER_GREEN,
                width=1
            )

            self._track_rings.append(
                (item_id, radius_fraction, width_scale)
            )

        # Animated segmented rings
        self._create_ring_segments(
            0.92,
            tuple((index * 45, 27) for index in range(8)),
            NEON_GREEN,
            3.4,
            -0.65
        )

        self._create_ring_segments(
            0.80,
            tuple((18 + index * 45, 28) for index in range(8)),
            MEDIUM_GREEN,
            3.0,
            0.95
        )

        self._create_ring_segments(
            0.66,
            tuple((index * 60, 32) for index in range(6)),
            NEON_GREEN,
            2.4,
            -0.38
        )

        self._create_ring_segments(
            0.49,
            tuple((30 + index * 90, 42) for index in range(4)),
            MEDIUM_GREEN,
            1.8,
            0.55
        )

        self._create_reactor_details()

        # Central energy core
        self.core_glow_id = self.core_canvas.create_oval(
            0, 0, 1, 1,
            fill=SURFACE_COLOR,
            outline=MEDIUM_GREEN,
            width=1
        )

        # Central hexagon
        self.core_hex_id = self.core_canvas.create_polygon(
            0, 0,
            1, 1,
            0, 0,
            1, 1,
            0, 0,
            1, 1,
            fill="",
            outline=MEDIUM_GREEN,
            width=1
        )

        # Reactor text
        self.core_text_id = self.core_canvas.create_text(
            125,
            125,
            text="BREAKER",
            fill=NEON_GREEN,
            font=("Arial", 16, "bold")
        )

        # Resize support
        self.core_canvas.bind(
            "<Configure>",
            self._on_canvas_configure,
            add="+"
        )

        # Bottom area reserved for command controls
        self.input_reserve = ctk.CTkFrame(
            self.center_panel,
            height=175,
            fg_color=SURFACE_COLOR,
            corner_radius=10
        )

        self.input_reserve.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(0, 6)
        )


    # ========================================================
    # REACTOR GEOMETRY
    # ========================================================

    def _create_ring_segments(
        self,
        radius_fraction,
        segments,
        color,
        width_scale,
        rotation_speed
    ):

        for start_angle, extent in segments:

            item_id = self.core_canvas.create_arc(
                0, 0, 1, 1,
                start=start_angle,
                extent=extent,
                style=tk.ARC,
                outline=color,
                width=1
            )

            self._ring_segments.append(
                (
                    item_id,
                    start_angle,
                    rotation_speed,
                    radius_fraction,
                    width_scale
                )
            )

    def _create_reactor_details(self):

        # Outer radial ticks
        for tick_index in range(72):

            is_major = tick_index % 6 == 0

            item_id = self.core_canvas.create_line(
                0, 0, 0, 0,
                fill=MEDIUM_GREEN if is_major else BORDER_GREEN,
                width=1
            )

            self._tick_items.append(
                (
                    item_id,
                    tick_index * 5,
                    0.915 if is_major else 0.94,
                    0.982,
                    1.35 if is_major else 0.85
                )
            )

        # Inner radial ticks
        for tick_index in range(48):

            is_major = tick_index % 4 == 0

            item_id = self.core_canvas.create_line(
                0, 0, 0, 0,
                fill=MEDIUM_GREEN if is_major else BORDER_GREEN,
                width=1
            )

            self._tick_items.append(
                (
                    item_id,
                    tick_index * 7.5,
                    0.685 if is_major else 0.70,
                    0.735,
                    1.1 if is_major else 0.75
                )
            )

        # Rotating scanner elements
        scanner_configurations = (
            (30, 0.70, 0.77, -1.25),
            (150, 0.70, 0.77, -1.25),
            (270, 0.70, 0.77, -1.25),
            (75, 0.51, 0.56, 1.6),
            (195, 0.51, 0.56, 1.6),
            (315, 0.51, 0.56, 1.6)
        )

        for start_angle, inner_radius, outer_radius, speed in scanner_configurations:

            item_id = self.core_canvas.create_line(
                0, 0, 0, 0,
                fill=MEDIUM_GREEN,
                width=2
            )

            self._scanner_items.append(
                (
                    item_id,
                    start_angle,
                    inner_radius,
                    outer_radius,
                    speed
                )
            )

        # Orbiting indicators
        indicator_configurations = (
            (0, 0.61, 1.1),
            (120, 0.61, 1.1),
            (240, 0.61, 1.1),
            (60, 0.85, -0.7),
            (180, 0.85, -0.7),
            (300, 0.85, -0.7)
        )

        for start_angle, radius_fraction, speed in indicator_configurations:

            item_id = self.core_canvas.create_oval(
                0, 0, 1, 1,
                fill=NEON_GREEN,
                outline=BG_COLOR
            )

            self._indicator_items.append(
                (
                    item_id,
                    start_angle,
                    radius_fraction,
                    speed
                )
            )

    # ========================================================
    # RESPONSIVE REACTOR LAYOUT
    # ========================================================

    def _on_canvas_configure(self, event):
        self._layout_reactor(event.width, event.height)

    def _layout_reactor(self, width, height):

        if width < 80 or height < 80:
            return

        size = (width, height)

        if size == self._last_reactor_size:
            return

        self._last_reactor_size = size

        self._reactor_center_x = width / 2
        self._reactor_center_y = height / 2

        self._reactor_radius = min(width, height) * 0.44
        self._reactor_scale = self._reactor_radius / 120

        # Resize track rings
        for item_id, radius_fraction, width_scale in self._track_rings:

            radius = self._reactor_radius * radius_fraction

            self.core_canvas.coords(
                item_id,
                self._reactor_center_x - radius,
                self._reactor_center_y - radius,
                self._reactor_center_x + radius,
                self._reactor_center_y + radius
            )

            self.core_canvas.itemconfigure(
                item_id,
                width=max(1, self._reactor_scale * width_scale)
            )

        # Resize animated arcs
        for item_id, _, _, radius_fraction, width_scale in self._ring_segments:

            radius = self._reactor_radius * radius_fraction

            self.core_canvas.coords(
                item_id,
                self._reactor_center_x - radius,
                self._reactor_center_y - radius,
                self._reactor_center_x + radius,
                self._reactor_center_y + radius
            )

            self.core_canvas.itemconfigure(
                item_id,
                width=max(1, self._reactor_scale * width_scale)
            )

        # Resize tick marks
        for item_id, angle, inner_fraction, outer_fraction, width_scale in self._tick_items:

            inner_x, inner_y = self._point_on_ring(
                inner_fraction,
                angle
            )

            outer_x, outer_y = self._point_on_ring(
                outer_fraction,
                angle
            )

            self.core_canvas.coords(
                item_id,
                inner_x,
                inner_y,
                outer_x,
                outer_y
            )

            self.core_canvas.itemconfigure(
                item_id,
                width=max(1, self._reactor_scale * width_scale)
            )

        # Resize central energy core
        core_radius = self._reactor_radius * 0.38

        self.core_canvas.coords(
            self.core_glow_id,
            self._reactor_center_x - core_radius,
            self._reactor_center_y - core_radius,
            self._reactor_center_x + core_radius,
            self._reactor_center_y + core_radius
        )

        # Rebuild hexagon geometry
        hex_radius = self._reactor_radius * 0.29

        hex_points = []

        for vertex in range(6):

            point = self._point_on_ring(
                hex_radius / self._reactor_radius,
                30 + vertex * 60
            )

            hex_points.extend(point)

        self.core_canvas.coords(
            self.core_hex_id,
            *hex_points
        )

        self.core_canvas.itemconfigure(
            self.core_glow_id,
            width=max(1, self._reactor_scale * 2)
        )

        self.core_canvas.itemconfigure(
            self.core_hex_id,
            width=max(1, self._reactor_scale * 1.5)
        )

        self.core_canvas.coords(
            self.core_text_id,
            self._reactor_center_x,
            self._reactor_center_y
        )

        self.core_canvas.itemconfigure(
            self.core_text_id,
            font=(
                "Arial",
                max(10, round(self._reactor_radius * 0.12)),
                "bold"
            )
        )

        self._position_scan_items()

    def _point_on_ring(self, radius_fraction, angle_degrees):

        angle = math.radians(angle_degrees)

        radius = self._reactor_radius * radius_fraction

        return (
            self._reactor_center_x + math.cos(angle) * radius,
            self._reactor_center_y - math.sin(angle) * radius
        )

    def _position_scan_items(self):

        # Moving scanner lines
        for item_id, initial_angle, inner_fraction, outer_fraction, speed in self._scanner_items:

            angle = initial_angle + self._animation_phase * speed

            inner_x, inner_y = self._point_on_ring(
                inner_fraction,
                angle
            )

            outer_x, outer_y = self._point_on_ring(
                outer_fraction,
                angle
            )

            self.core_canvas.coords(
                item_id,
                inner_x,
                inner_y,
                outer_x,
                outer_y
            )

        # Moving orbit indicators
        indicator_size = max(
            2,
            self._reactor_radius * 0.018
        )

        for item_id, initial_angle, radius_fraction, speed in self._indicator_items:

            angle = initial_angle + self._animation_phase * speed

            center_x, center_y = self._point_on_ring(
                radius_fraction,
                angle
            )

            self.core_canvas.coords(
                item_id,
                center_x - indicator_size,
                center_y - indicator_size,
                center_x + indicator_size,
                center_y + indicator_size
            )

    # ========================================================
    # ANIMATION
    # ========================================================

    @staticmethod
    def _blend_color(start_color, end_color, amount):

        start = tuple(
            int(start_color[index:index + 2], 16)
            for index in (1, 3, 5)
        )

        end = tuple(
            int(end_color[index:index + 2], 16)
            for index in (1, 3, 5)
        )

        blended = tuple(
            round(first + (second - first) * amount)
            for first, second in zip(start, end)
        )

        return "#{:02X}{:02X}{:02X}".format(*blended)

    def _update_animation(self):

        self._animation_frame += 1
        profile = REACTOR_PROFILES[self._reactor_state]
        speed_multiplier = profile["speed"]

        self._animation_phase += speed_multiplier

        # Rotate arc segments
        for item_id, initial_angle, rotation_speed, _, _ in self._ring_segments:

            self.core_canvas.itemconfigure(
                item_id,
                start=(
                    initial_angle
                    + self._animation_phase * rotation_speed
                ) % 360
            )

        self._position_scan_items()

        # Pulsing central core
        pulse = (
            math.sin(self._animation_frame * 0.08) + 1
        ) / 2

        self.core_canvas.itemconfigure(
            self.core_glow_id,
            outline=self._blend_color(
                BORDER_GREEN,
                profile["color"],
                pulse
            ),
            width=self._reactor_scale * (1.5 + pulse)
        )

    def _schedule_animation(self):

        if not self._animation_stopped:

            self._animation_after_id = self.after(
                33,
                self._animate
            )

    def _animate(self):

        self._animation_after_id = None

        if self._animation_stopped:
            return

        self._update_animation()
        self._schedule_animation()

    def _on_destroy(self, event):

        if event.widget is not self:
            return

        if self._cleanup_done is True:
            return

        self._cleanup_done = True
        self._animation_stopped = True

        if self._animation_after_id is not None:

            try:
                self.after_cancel(
                    self._animation_after_id
                )

            except tk.TclError:
                pass

            finally:
                self._animation_after_id = None

        if self._worker_poll_after_id is not None:
            try:
                self.after_cancel(self._worker_poll_after_id)

            except tk.TclError:
                pass

            finally:
                self._worker_poll_after_id = None

        if (self._controller is not None
            and self._pending_action_id is not None
            and self._active_action_id is None):

            action_id = self._pending_action_id
            try:
                self._controller.cancel_action(action_id)

            except ActionApprovalError:
                pass

            else:
                self._pending_action_id = None

        if self._worker is not None:
            self._worker.shutdown()
    # ========================================================
    # SYSTEM STATUS PANEL
    # ========================================================

    def _build_status(self):

        self.system_status_label = ctk.CTkLabel(
            self.right_panel,
            text="HUD READY",
            text_color=NEON_GREEN,
            font=ctk.CTkFont(size=15)
        )

        self.system_status_label.pack(
            pady=(30, 20)
        )

        self.microphone_status_label = ctk.CTkLabel(
            self.right_panel,
            text="MICROPHONE OFF",
            text_color=MUTED_TEXT,
            font=ctk.CTkFont(size=13)
        )

        self.microphone_status_label.pack(
            pady=15
        )

        model_label = ctk.CTkLabel(
            self.right_panel,
            text="MODEL NOT CONNECTED",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(size=12)
        )

        model_label.pack(
            pady=15
        )

        activity_label = ctk.CTkLabel(
            self.right_panel,
            text="No pending action",
            text_color=MUTED_TEXT,
            font=ctk.CTkFont(size=12)
        )

        activity_label.pack(
            pady=15
        )

    def set_system_status(self, message):

        self.system_status_label.configure(
            text=message
        )

    def _set_reactor_state(self, new_state):
        if new_state not in REACTOR_PROFILES:
            raise ValueError("Unknown reactor state")

        self._reactor_state = new_state

    # ========================================================
    # MEMORY COMMAND CONTROLS
    # ========================================================

    def _build_memory_controls(self):

        # Reuse the reserved bottom frame.
        self.command_panel = self.input_reserve

        self.command_panel.grid_columnconfigure(
            0,
            weight=1
        )

        self.command_panel.grid_columnconfigure(
            1,
            weight=0
        )

        # Memory entry
        self.memory_entry = ctk.CTkEntry(
            self.command_panel,
            placeholder_text="Enter a memory for Breaker...",
            fg_color=BG_COLOR,
            text_color=TEXT_COLOR,
            border_color=BORDER_GREEN,
            height=38
        )

        self.memory_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(12, 6),
            pady=(12, 5)
        )

        # Preview button
        self.preview_button = ctk.CTkButton(
            self.command_panel,
            text="Preview",
            command=self._preview_memory,
            fg_color=NEON_GREEN,
            text_color=BG_COLOR,
            hover_color=MEDIUM_GREEN,
            width=100,
            height=38,
            state=(
                "normal"
                if self._controller is not None
                else "disabled"
            )
        )

        self.preview_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(6, 12),
            pady=(12, 5)
        )

        # Proposal preview
        self.memory_preview_text = create_read_only_textbox(
            self.command_panel,
            "No pending action",
            width=550,
            height=80,
            text_color=TEXT_COLOR,
            fg_color=SURFACE_COLOR,
            font=ctk.CTkFont(size=12),
            border_width=0,
            border_spacing=6,
            corner_radius=0,
            scrollbar_button_color=BORDER_GREEN,
            scrollbar_button_hover_color=MEDIUM_GREEN,
        )

        self.memory_preview_text.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=12,
            pady=4
        )
        self.command_panel.grid_rowconfigure(1, weight=1)

        # Approval / cancellation row
        decision_row = ctk.CTkFrame(
            self.command_panel,
            fg_color="transparent"
        )

        decision_row.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="e",
            padx=12,
            pady=(4, 10)
        )

        # Approve button
        self.approve_button = ctk.CTkButton(
            decision_row,
            text="Approve",
            command=self._approve_memory,
            fg_color=MEDIUM_GREEN,
            hover_color=BORDER_GREEN,
            text_color=BG_COLOR,
            width=110,
            state="disabled"
        )

        self.approve_button.pack(
            side="left",
            padx=(0, 8)
        )

        # Cancel button
        self.cancel_button = ctk.CTkButton(
            decision_row,
            text="Cancel",
            command=self._cancel_memory,
            fg_color=PANEL_COLOR,
            hover_color=BORDER_GREEN,
            text_color=TEXT_COLOR,
            border_color=BORDER_GREEN,
            border_width=1,
            width=110,
            state="disabled"
        )

        self.cancel_button.pack(
            side="left"
        )

    # ========================================================
    # MEMORY PREVIEW
    # ========================================================

    def _preview_memory(self):

        if self._controller is None:
            return

        if self._active_action_id is not None:
            return

        if self._pending_action_id is not None:
            return

        content = self.memory_entry.get()

        try:
            proposal = self._controller.submit_memory(
                content
            )

        except BreakerActionError:
            self.set_system_status(
                "INVALID MEMORY CONTENT"
            )
            return

        self._pending_action_id = proposal["action_id"]

        # Show the exact normalized content.
        set_read_only_text(
            self.memory_preview_text, proposal["action_data"]["content"]
        )

        self.approve_button.configure(
            state="normal"
        )

        self.cancel_button.configure(
            state="normal"
        )

        self.preview_button.configure(
            state="disabled"
        )

        self.set_system_status(
            "AWAITING APPROVAL"
        )

        self._set_reactor_state("awaiting_approval")

    # ========================================================
    # RESET MEMORY CONTROLS
    # ========================================================

    def _reset_memory_controls(self):

        self._pending_action_id = None

        self.approve_button.configure(
            state="disabled"
        )

        self.cancel_button.configure(
            state="disabled"
        )

        self.preview_button.configure(
            state=(
                "normal"
                if self._controller is not None
                else "disabled"
            )
        )

        set_read_only_text(self.memory_preview_text, "No pending action")

    # ========================================================
    # APPROVE MEMORY
    # ========================================================

    def _approve_memory(self):

        if self._controller is None:
            return

        if self._worker is None:
            return

        if self._pending_action_id is None:
            return

        if self._active_action_id is not None:
            return
        
        action_id = self._pending_action_id

        # Prevent duplicate clicks.
        self.approve_button.configure(
            state = "disabled"
        )

        self.cancel_button.configure(
            state = "disabled"
        )

        self.preview_button.configure(
            state = "disabled"
        )

        self._set_reactor_state("executing")

        try:
            self._worker.start(action_id)

        except (ValueError, RuntimeError):
            self.approve_button.configure(state = "normal")
            self.cancel_button.configure(state = "normal")
            self._set_reactor_state("awaiting_approval")
            self.set_system_status("WORKER START FAILED")
            return

        self._active_action_id = action_id
        self._set_reactor_state("executing")
        self.set_system_status("EXECUTING MEMORY WRITE")

    # ========================================================
    # CANCEL MEMORY
    # ========================================================

    def _cancel_memory(self):

        if self._controller is None:
            return

        if self._active_action_id is not None:
            return

        if self._pending_action_id is None:
            return

        try:
            self._controller.cancel_action(
                self._pending_action_id
            )

        except ActionApprovalError:

            self.set_system_status(
                "CANCEL FAILED"
            )

            return

        self._reset_memory_controls()
        self._set_reactor_state("canceled")
        self.set_system_status(
            "ACTION CANCELED"
        )

    def _schedule_worker_poll(self):
        if self._animation_stopped == True:
            return

        if self._worker is None:
            return

        if self._worker_poll_after_id != None:
            return

        self._worker_poll_after_id = self.after(50, self._poll_worker_results)

    def _poll_worker_results(self):
        self._worker_poll_after_id = None

        if self._animation_stopped is True:
            return

        if self._worker is None:
            return

        while True:
            try:
                event = self._worker.results.get_nowait()

            except queue.Empty:
                break

            if event.get("action_id") != self._active_action_id:
                continue

            self._active_action_id = None
            self._reset_memory_controls()

            if event.get("success") is True and event.get("status") == "completed":
                self._reactor_state = "completed"

                if self._demo_mode:
                    self.set_system_status("DEMO ACTION COMPLETED - NOT SAVED")

                else:
                    self.set_system_status("MEMORY WRITE CONFIRMED")

            else:
                self._reactor_state = "error"
                self.set_system_status("MEMORY WRITE FAILED")
        self._schedule_worker_poll()