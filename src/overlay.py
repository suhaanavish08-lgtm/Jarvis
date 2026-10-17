"""Top-center, voice-synced transparent visual overlay for Jarvis."""

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

# 100x100 window at top-center of screen
screen_width = root.winfo_screenwidth()
x = int(screen_width / 2 - 50)
y = 10
root.geometry(f"100x100+{x}+{y}")

canvas = tk.Canvas(root, width=100, height=100, bg="black", highlightthickness=0)
canvas.pack(fill="both", expand=True)

# Draw cyan orb at center (50, 50)
orb = canvas.create_oval(0, 0, 0, 0, fill="cyan", outline="")

# Initially hidden since state is idle
try:
    root.withdraw()
except Exception:
    pass


def update_animation():
    """Update orb radius and window visibility based on JARVIS_STATE."""
    global JARVIS_STATE
    cx, cy = 50, 50

    try:
        if JARVIS_STATE == "idle":
            canvas.coords(orb, 0, 0, 0, 0)
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
            # Pulse radius smoothly using math.sin(time.time() * 5)
            radius = 27 + 9 * math.sin(time.time() * 5)
            canvas.coords(orb, cx - radius, cy - radius, cx + radius, cy + radius)
        elif JARVIS_STATE == "speaking":
            try:
                if root.state() == "withdrawn":
                    root.deiconify()
            except Exception:
                pass
            # Modulate radius rapidly using random.uniform to simulate real-time voice lip-syncing
            radius = random.uniform(16, 42)
            canvas.coords(orb, cx - radius, cy - radius, cx + radius, cy + radius)
    except Exception:
        pass

    try:
        root.after(30, update_animation)
    except Exception:
        pass


# Register animation loop
root.after(30, update_animation)
