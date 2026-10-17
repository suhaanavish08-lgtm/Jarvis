"""Top-center, voice-synced transparent visual overlay for Jarvis."""

import math
import random
import time
import tkinter as tk

JARVIS_STATE = "idle"
current_radius = 0.0

root = tk.Tk()
root.title("Jarvis Overlay")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="black")
root.attributes("-transparentcolor", "black")

# 150x150 window positioned exactly top-center of screen
w = 150
x = int((root.winfo_screenwidth() - w) / 2)
y = 10
root.geometry(f"{w}x150+{x}+{y}")

canvas = tk.Canvas(root, width=w, height=150, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)

# 3 concentric cyan ovals for rich HUD visual appearance
oval_outer = canvas.create_oval(0, 0, 0, 0, fill="#003b46", outline="#00ffff", width=2)
oval_mid = canvas.create_oval(0, 0, 0, 0, fill="#007f99", outline="#80ffff", width=1)
oval_inner = canvas.create_oval(0, 0, 0, 0, fill="#00ffff", outline="")
ovals = [oval_outer, oval_mid, oval_inner]
orb = oval_inner  # Backward compatibility alias

# Initially hidden since state is idle
try:
    root.withdraw()
except Exception:
    pass


def update_animation():
    """Update orb radius and window visibility based on JARVIS_STATE with fluid target smoothing."""
    global JARVIS_STATE, current_radius
    cx, cy = w / 2, 75.0

    try:
        if JARVIS_STATE == "idle":
            current_radius = 0.0
            for oval in ovals:
                canvas.coords(oval, 0, 0, 0, 0)
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
            # Pulse smoothly using math.sin(time.time() * 5)
            target_radius = 38.0 + 10.0 * math.sin(time.time() * 5)
            current_radius += (target_radius - current_radius) * 0.3

            r_out = max(0.0, current_radius)
            r_mid = max(0.0, current_radius * 0.68)
            r_in = max(0.0, current_radius * 0.36)

            canvas.coords(oval_outer, cx - r_out, cy - r_out, cx + r_out, cy + r_out)
            canvas.coords(oval_mid, cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid)
            canvas.coords(oval_inner, cx - r_in, cy - r_in, cx + r_in, cy + r_in)
        elif JARVIS_STATE == "speaking":
            try:
                if root.state() == "withdrawn":
                    root.deiconify()
            except Exception:
                pass
            # Modulate radius rapidly using random.uniform with target smoothing for fluid pulsing
            target_radius = random.uniform(25.0, 58.0)
            current_radius += (target_radius - current_radius) * 0.3

            r_out = max(0.0, current_radius)
            r_mid = max(0.0, current_radius * 0.68)
            r_in = max(0.0, current_radius * 0.36)

            canvas.coords(oval_outer, cx - r_out, cy - r_out, cx + r_out, cy + r_out)
            canvas.coords(oval_mid, cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid)
            canvas.coords(oval_inner, cx - r_in, cy - r_in, cx + r_in, cy + r_in)
    except Exception:
        pass

    try:
        root.after(30, update_animation)
    except Exception:
        pass


# Register animation loop
root.after(30, update_animation)
