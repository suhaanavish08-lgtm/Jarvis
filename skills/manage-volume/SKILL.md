---
name: manage-volume
description: Control Windows system audio volume. Can increase, decrease, mute, unmute, or set volume to a specific percentage. Use when the user requests audio volume adjustments.
license: MIT
compatibility: Windows with pycaw audio endpoint
metadata:
  version: "0.1.0"
  author: "jarvis"
---

# Manage Volume Skill

Adjusts Windows system volume levels using the pycaw audio endpoint API with PyAutoGUI fallback.

## Parameters
- `action` (string, required): "up", "down", "mute", "unmute", or "set"
- `value` (integer, optional): Target percentage level (0-100) or step amount
