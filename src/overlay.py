"""Compact top title-bar gradient waveform visualizer for Jarvis."""

import ctypes
import math
import random
import time
import tkinter as tk

# Enable Per-Monitor DPI Awareness so Tkinter screen width and placement align with physical monitor pixels
try:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

JARVIS_STATE = "idle"


def get_gradient_color(t: float) -> str:
    """Interpolate gradient from #00f3ff (cyan) to #9d00ff (purple)."""
    r = int(0 + t * (157 - 0))
    g = int(243 + t * (0 - 243))
    b = 255
    return f"#{r:02x}{g:02x}{b:02x}"


class CompactVisualizer:
    """Compact Title-Bar Visualizer with pre-allocated lines to avoid frame drops."""

    def __init__(self, root_window: tk.Tk = None):
        if root_window is None:
            root_window = tk.Tk()
        self.root = root_window
        self.root.title("Jarvis Visualizer")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg="black")
        self.root.attributes("-transparentcolor", "black")

        # Set window dimensions to width = 240, height = 30
        self.w = 240
        self.h = 30
        screen_w = self.root.winfo_screenwidth()
        self.x = int((screen_w - 240) / 2)
        self.y = 2
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")

        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Pre-allocate 30 vertical canvas lines (cyan-to-purple gradient)
        self.num_lines = 30
        self.spacing = 7.0
        self.total_span = (self.num_lines - 1) * self.spacing
        self.start_x = (self.w - self.total_span) / 2.0
        self.cy = self.h / 2.0  # 15.0 px

        self.lines = []
        self.line_colors = []
        for i in range(self.num_lines):
            t = i / float(self.num_lines - 1)
            color = get_gradient_color(t)
            self.line_colors.append(color)
            lx = self.start_x + i * self.spacing
            # Pre-allocate vertical canvas line; initially static 2px flat center line
            line = self.canvas.create_line(lx, self.cy - 1.0, lx, self.cy + 1.0, fill=color, width=2)
            self.lines.append(line)

        # Backward compatibility aliases
        self.bars = self.lines
        self.dots = self.lines
        self.ovals = self.lines
        self.orb = self.lines[0]
        self.num_bars = self.num_lines
        self.bar_colors = self.line_colors
        self.DOT_COLORS = [self.line_colors[0], self.line_colors[10], self.line_colors[20], self.line_colors[-1]]
        self.current_heights = [2.0] * self.num_lines

    def update_animation(self):
        """Iterate through lines and solely update their Y-coordinates without deleting canvas items."""
        global JARVIS_STATE
        now = time.time()

        try:
            if JARVIS_STATE == "idle":
                # Idle state: render a static 2px flat center line
                for i, line_id in enumerate(self.lines):
                    lx = self.start_x + i * self.spacing
                    self.current_heights[i] = 2.0
                    self.canvas.coords(line_id, lx, self.cy - 1.0, lx, self.cy + 1.0)

            elif JARVIS_STATE == "listening":
                # Listening state: subtle 8px sine wave
                for i, line_id in enumerate(self.lines):
                    lx = self.start_x + i * self.spacing
                    wave = math.sin(now * 6.0 + i * 0.25)
                    h_i = 2.0 + 6.0 * abs(wave)  # subtle 8px sine wave
                    self.current_heights[i] = h_i
                    half = h_i / 2.0
                    self.canvas.coords(line_id, lx, self.cy - half, lx, self.cy + half)

            elif JARVIS_STATE == "speaking":
                # Speaking state: smooth 20px dynamic modulated wave
                for i, line_id in enumerate(self.lines):
                    lx = self.start_x + i * self.spacing
                    target = random.uniform(4.0, 20.0)
                    self.current_heights[i] += (target - self.current_heights[i]) * 0.35
                    h_i = max(2.0, min(20.0, self.current_heights[i]))
                    half = h_i / 2.0
                    self.canvas.coords(line_id, lx, self.cy - half, lx, self.cy + half)

        except Exception:
            pass

        # Throttle Tkinter loop: 200ms when idle to sleep CPU, 16ms (60 FPS) when listening/speaking
        delay = 200 if JARVIS_STATE == "idle" else 16
        try:
            self.root.after(delay, self.update_animation)
        except Exception:
            pass


# Class alias
VisualizerOverlay = CompactVisualizer

# Module-level default instance and properties
_visualizer = CompactVisualizer()
root = _visualizer.root
canvas = _visualizer.canvas
w = _visualizer.w
h = _visualizer.h
x = _visualizer.x
y = _visualizer.y
num_lines = _visualizer.num_lines
spacing = _visualizer.spacing
total_span = _visualizer.total_span
start_x = _visualizer.start_x
cy = _visualizer.cy
lines = _visualizer.lines
line_colors = _visualizer.line_colors
bars = _visualizer.bars
dots = _visualizer.dots
ovals = _visualizer.ovals
orb = _visualizer.orb
num_bars = _visualizer.num_bars
bar_colors = _visualizer.bar_colors
DOT_COLORS = _visualizer.DOT_COLORS
current_heights = _visualizer.current_heights


def update_animation():
    """Module-level entry point forwarding to active visualizer."""
    _visualizer.update_animation()


root.after(200, update_animation)
