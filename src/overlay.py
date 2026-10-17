"""Top-center header gradient waveform visualizer for Jarvis."""

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

root = tk.Tk()
root.title("Jarvis Visualizer")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="black")
root.attributes("-transparentcolor", "black")

# 480x60 window positioned dead center inside the top header area
w = 480
h = 60
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
x = int((screen_w - w) / 2)
y = 2
root.geometry(f"{w}x{h}+{x}+{y}")

canvas = tk.Canvas(root, width=w, height=h, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)


def get_gradient_color(t: float) -> str:
    """Interpolate gradient from #00f3ff (cyan) to #4a80ff (blue) to #9d00ff (purple)."""
    if t <= 0.5:
        factor = t / 0.5
        r = int(0 + factor * (74 - 0))
        g = int(243 + factor * (128 - 243))
        b = 255
    else:
        factor = (t - 0.5) / 0.5
        r = int(74 + factor * (157 - 74))
        g = int(128 + factor * (0 - 128))
        b = 255
    return f"#{r:02x}{g:02x}{b:02x}"


num_lines = 40
spacing = 10.5
total_span = (num_lines - 1) * spacing
start_x = (w - total_span) / 2.0
cy = h / 2.0  # 30.0 px

lines = []
line_colors = []
for i in range(num_lines):
    t = i / float(num_lines - 1)
    color = get_gradient_color(t)
    line_colors.append(color)
    lx = start_x + i * spacing
    # Pre-create 40 persistent canvas line items with line width 4
    line = canvas.create_line(lx, cy - 3.0, lx, cy + 3.0, fill=color, width=4)
    lines.append(line)

# Backward-compatibility aliases
bars = lines
dots = lines
ovals = lines
orb = lines[0]
num_bars = num_lines
bar_colors = line_colors
DOT_COLORS = [line_colors[0], line_colors[10], line_colors[20], line_colors[-1]]

current_heights = [6.0] * num_lines


def update_animation():
    """Update top-center header visualizer lines using canvas.coords without redrawing canvas."""
    global JARVIS_STATE, current_heights
    now = time.time()

    try:
        if JARVIS_STATE == "idle":
            # Idle state: visible, elegant breathing waveform
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                h_i = 6.0 + 4.0 * math.sin(now * 3.0 + i * 0.22)
                current_heights[i] = h_i
                half = h_i / 2.0
                canvas.coords(line_id, lx, cy - half, lx, cy + half)

        elif JARVIS_STATE == "listening":
            # Listening state: undulating 30px sine wave
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                wave = math.sin(now * 6.5 + i * 0.22)
                h_i = 8.0 + 22.0 * abs(wave)
                current_heights[i] = h_i
                half = h_i / 2.0
                canvas.coords(line_id, lx, cy - half, lx, cy + half)

        elif JARVIS_STATE == "speaking":
            # Speaking state: dynamic 48px fluid wave
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                target = random.uniform(8.0, 48.0)
                current_heights[i] += (target - current_heights[i]) * 0.35
                h_i = max(6.0, min(50.0, current_heights[i]))
                half = h_i / 2.0
                canvas.coords(line_id, lx, cy - half, lx, cy + half)

    except Exception:
        pass

    try:
        root.after(20, update_animation)
    except Exception:
        pass


root.after(20, update_animation)
