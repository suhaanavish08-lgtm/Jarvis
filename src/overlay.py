"""Top-center gradient waveform visualizer for Jarvis."""

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

# 500x120 window positioned dead center right beneath camera
w = 500
h = 120
x = int((root.winfo_screenwidth() - w) / 2)
y = 10
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


num_bars = 50
bar_w = 4.0
bar_spacing = 8.0
total_width = (num_bars - 1) * bar_spacing + bar_w
start_x = (w - total_width) / 2.0
cy = (h - 24) / 2.0  # vertical center for waveform bars

bars = []
bar_colors = []
for i in range(num_bars):
    t = i / float(num_bars - 1)
    color = get_gradient_color(t)
    bar_colors.append(color)
    bx = start_x + i * bar_spacing
    bar = canvas.create_rectangle(bx, cy - 2, bx + bar_w, cy + 2, fill=color, outline="")
    bars.append(bar)

status_text = canvas.create_text(w / 2, h - 14, text="", fill="#a0a0b0", font=("Segoe UI", 9, "bold"))

# Aliases for backward compatibility
dots = bars
ovals = bars
orb = bars[0]
DOT_COLORS = [bar_colors[0], bar_colors[len(bar_colors) // 3], bar_colors[2 * len(bar_colors) // 3], bar_colors[-1]]

current_heights = [4.0] * num_bars
target_heights = [4.0] * num_bars

# Initially hidden or subtle
try:
    root.withdraw()
except Exception:
    pass


def update_animation():
    """Update top-center gradient waveform animation at 60 FPS."""
    global JARVIS_STATE, current_heights, target_heights
    now = time.time()

    try:
        if JARVIS_STATE == "idle":
            # Tiny flat/breathing waveform with minor offset motion
            canvas.itemconfig(status_text, text="")
            for i, bar in enumerate(bars):
                bx = start_x + i * bar_spacing
                h_i = max(2.0, 3.0 + 1.8 * math.sin(now * 2.5 + i * 0.12))
                current_heights[i] = h_i
                canvas.coords(bar, bx, cy - h_i / 2.0, bx + bar_w, cy + h_i / 2.0)
            try:
                if root.state() != "withdrawn":
                    root.withdraw()
            except Exception:
                pass

        elif JARVIS_STATE == "listening":
            try:
                if root.state() == "withdrawn":
                    root.deiconify()
            except Exception:
                pass

            canvas.itemconfig(status_text, text="LISTENING...", fill="#00f3ff")
            amplitude = 26.0
            for i, bar in enumerate(bars):
                bx = start_x + i * bar_spacing
                # Sequential height modulation producing undulating double humps
                wave = math.sin(now * 8.0 + i * 0.15)
                h_i = max(3.0, abs(wave) * amplitude + 4.0)
                current_heights[i] = h_i
                canvas.coords(bar, bx, cy - h_i / 2.0, bx + bar_w, cy + h_i / 2.0)

        elif JARVIS_STATE == "speaking":
            try:
                if root.state() == "withdrawn":
                    root.deiconify()
            except Exception:
                pass

            canvas.itemconfig(status_text, text="RECOGNIZING...", fill="#d0a0ff")
            for i, bar in enumerate(bars):
                bx = start_x + i * bar_spacing
                target = random.uniform(6.0, 50.0)
                current_heights[i] += (target - current_heights[i]) * 0.35
                h_i = current_heights[i]
                canvas.coords(bar, bx, cy - h_i / 2.0, bx + bar_w, cy + h_i / 2.0)

    except Exception:
        pass

    try:
        root.after(16, update_animation)
    except Exception:
        pass


root.after(16, update_animation)
