"""Bottom-center, Google Assistant-style animated multi-dot transparent visual overlay for Jarvis."""

import math
import random
import time
import tkinter as tk

JARVIS_STATE = "idle"

root = tk.Tk()
root.title("Jarvis Overlay")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="black")
root.attributes("-transparentcolor", "black")

# Window placement centered accurately at bottom of screen: w = 300, h = 100
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
w = 300
h = 100
x = int((screen_w - w) / 2)
y = screen_h - 120
root.geometry(f"{w}x{h}+{x}+{y}")

canvas = tk.Canvas(root, width=w, height=h, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)

# Google Dots: Blue (#4285F4), Red (#EA4335), Yellow (#FBBC05), Green (#34A853)
DOT_COLORS = ["#4285F4", "#EA4335", "#FBBC05", "#34A853"]
# Four horizontal dots spaced evenly across the center of the canvas (width=300, center=150)
dot_x_positions = [90.0, 130.0, 170.0, 210.0]
dots = [
    canvas.create_oval(0, 0, 0, 0, fill=color, outline="")
    for color in DOT_COLORS
]
ovals = dots  # Backward compatibility alias
orb = dots[0]  # Backward compatibility alias

current_radii = [0.0, 0.0, 0.0, 0.0]
current_radius = 0.0

# Initially hidden since state is idle
try:
    root.withdraw()
except Exception:
    pass


def update_animation():
    """Update Google-style dots animation (60 FPS) and window visibility based on JARVIS_STATE."""
    global JARVIS_STATE, current_radii, current_radius
    cy = h / 2.0

    try:
        if JARVIS_STATE == "idle":
            current_radii = [0.0, 0.0, 0.0, 0.0]
            current_radius = 0.0
            for dot in dots:
                canvas.coords(dot, 0, 0, 0, 0)
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

            # Wave effect: smooth math.sin wave modulating Y-coordinate of each dot
            # Offset increases for each dot from left to right (0.0, 0.75, 1.5, 2.25)
            # Perfect 20x20 circles (r = 10.0) ensuring width and height of bounding box are identical
            r = 10.0
            now = time.time()
            for i, dot in enumerate(dots):
                offset = i * 0.75
                bounce = 12.0 * math.sin(now * 4.5 + offset)
                dot_y = cy + bounce
                dot_x = dot_x_positions[i]
                canvas.coords(dot, dot_x - r, dot_y - r, dot_x + r, dot_y + r)

        elif JARVIS_STATE == "speaking":
            try:
                if root.state() == "withdrawn":
                    root.deiconify()
            except Exception:
                pass

            # Apply target-smoothing algorithm: current_radius += (target_radius - current_radius) * 0.3
            # Perfect circular pulsing ensuring identical width and height bounding boxes
            for i, dot in enumerate(dots):
                target_radius = random.uniform(7.0, 16.0)
                current_radii[i] += (target_radius - current_radii[i]) * 0.3
                r = current_radii[i]
                dot_x = dot_x_positions[i]
                canvas.coords(dot, dot_x - r, cy - r, dot_x + r, cy + r)
            current_radius = current_radii[0]

    except Exception:
        pass

    try:
        # Upgrade animation loop to 60 FPS (16ms)
        root.after(16, update_animation)
    except Exception:
        pass


# Register animation loop at 60 FPS
root.after(16, update_animation)
