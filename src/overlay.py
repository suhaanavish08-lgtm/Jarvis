"""Compact top title-bar gradient waveform visualizer for Jarvis."""

import math
import random
import time
import tkinter as tk

JARVIS_STATE = "idle"

root = tk.Tk()
root.title("Jarvis Visualizer")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="black")
root.attributes("-transparentcolor", "black")

# 240x30 window positioned dead center inside the top title bar
w = 240
h = 30
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
x = int((screen_w - w) / 2)
y = 2
root.geometry(f"{w}x{h}+{x}+{y}")

canvas = tk.Canvas(root, width=w, height=h, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)


def get_gradient_color(t: float) -> str:
    """Interpolate gradient from #00f3ff (cyan) to #9d00ff (purple)."""
    r = int(0 + t * (157 - 0))
    g = int(243 + t * (0 - 243))
    b = 255
    return f"#{r:02x}{g:02x}{b:02x}"


num_lines = 30
spacing = 7.0
total_span = (num_lines - 1) * spacing
start_x = (w - total_span) / 2.0
cy = h / 2.0  # 15.0 px

lines = []
line_colors = []
for i in range(num_lines):
    t = i / float(num_lines - 1)
    color = get_gradient_color(t)
    line_colors.append(color)
    lx = start_x + i * spacing
    # Pre-create 30 persistent canvas line items (initially thin 2px center line)
    line = canvas.create_line(lx, cy - 1.0, lx, cy + 1.0, fill=color, width=2)
    lines.append(line)

# Backward-compatibility aliases
bars = lines
dots = lines
ovals = lines
orb = lines[0]
num_bars = num_lines
bar_colors = line_colors
DOT_COLORS = [line_colors[0], line_colors[10], line_colors[20], line_colors[-1]]

current_heights = [2.0] * num_lines


def update_animation():
    """Update compact title-bar visualizer lines using canvas.coords (no canvas.delete)."""
    global JARVIS_STATE, current_heights
    now = time.time()

    try:
        if JARVIS_STATE == "idle":
            # Idle state: thin 2px center line
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                current_heights[i] = 2.0
                canvas.coords(line_id, lx, cy - 1.0, lx, cy + 1.0)

        elif JARVIS_STATE == "listening":
            # Listening state: subtle 8px sine wave
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                wave = math.sin(now * 6.0 + i * 0.25)
                h_i = 2.0 + 6.0 * abs(wave)  # Peak height ~8px
                current_heights[i] = h_i
                half = h_i / 2.0
                canvas.coords(line_id, lx, cy - half, lx, cy + half)

        elif JARVIS_STATE == "speaking":
            # Speaking state: smooth 20px dynamic wave
            for i, line_id in enumerate(lines):
                lx = start_x + i * spacing
                target = random.uniform(4.0, 20.0)
                current_heights[i] += (target - current_heights[i]) * 0.35
                h_i = max(2.0, min(20.0, current_heights[i]))
                half = h_i / 2.0
                canvas.coords(line_id, lx, cy - half, lx, cy + half)

    except Exception:
        pass

    try:
        root.after(20, update_animation)
    except Exception:
        pass


root.after(20, update_animation)
