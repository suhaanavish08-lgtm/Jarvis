---
name: manage-brightness
description: Control screen brightness on Windows displays. Can increase, decrease, or set brightness to a specific percentage. Use when the user asks to adjust screen or display brightness.
license: MIT
compatibility: Windows with WMI or screen_brightness_control
metadata:
  version: "0.1.0"
  author: "jarvis"
---

# Manage Brightness Skill

Controls monitor brightness using screen_brightness_control with direct PowerShell WMI fallback.

## Parameters
- `action` (string, required): "up", "down", or "set"
- `value` (integer, optional): Target percentage level (0-100) or step amount
