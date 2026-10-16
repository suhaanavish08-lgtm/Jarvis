"""System control module for Jarvis: system stats, application launcher, and Spotify control."""

import os
import shutil
import subprocess
import sys
import urllib.parse
from typing import Dict, Any, Tuple, List
import psutil
import pyautogui

pyautogui.FAILSAFE = False


def get_system_stats() -> Dict[str, Any]:
    """Retrieve current system resource statistics (CPU, RAM, Disk, Battery)."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    virtual_mem = psutil.virtual_memory()
    
    # Disk usage for main system drive
    system_drive = os.getenv("SystemDrive", "C:") + "\\"
    disk = psutil.disk_usage(system_drive)
    
    battery = psutil.sensors_battery()
    battery_info = None
    if battery:
        battery_info = {
            "percent": round(battery.percent, 1),
            "power_plugged": battery.power_plugged,
        }

    stats = {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(virtual_mem.total / (1024 ** 3), 2),
            "used_gb": round(virtual_mem.used / (1024 ** 3), 2),
            "free_gb": round(virtual_mem.available / (1024 ** 3), 2),
            "percent": virtual_mem.percent,
        },
        "disk": {
            "drive": system_drive,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent,
        },
        "battery": battery_info,
    }
    
    summary = (
        f"CPU is running at {stats['cpu_percent']}%. "
        f"Memory usage is at {stats['memory']['percent']}% with {stats['memory']['free_gb']} GB available. "
        f"Disk {stats['disk']['drive']} has {stats['disk']['free_gb']} GB free."
    )
    if battery_info:
        plugged_str = "charging" if battery_info["power_plugged"] else "on battery"
        summary += f" Battery is at {battery_info['percent']}% ({plugged_str})."
        
    stats["summary"] = summary
    return stats


def _resolve_antigravity_path() -> str | None:
    """Find Antigravity IDE or executable path on the machine."""
    agy_cmd = shutil.which("antigravity") or shutil.which("antigravity-ide") or shutil.which("agy")
    if agy_cmd:
        return agy_cmd

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, "Programs", "Antigravity IDE", "Antigravity IDE.exe"),
        os.path.join(local_app_data, "Programs", "antigravity", "Antigravity.exe"),
        os.path.join(local_app_data, "Programs", "Antigravity IDE", "bin", "antigravity-ide.cmd"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def open_application(app_name: str) -> Tuple[bool, str]:
    """Launch designated applications using apps dictionary."""
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "spotify": "start spotify:",
        "spot if": "start spotify:",
        "antigravity": "antigravity",
    }

    name_clean = app_name.strip().lower()

    for key, command in apps.items():
        if key in name_clean:
            try:
                if key == "antigravity":
                    path = _resolve_antigravity_path()
                    if path:
                        subprocess.Popen([path], shell=False)
                        return True, "Antigravity launched successfully."
                
                subprocess.Popen(command, shell=True)
                return True, f"{key.capitalize()} opened."
            except Exception as e:
                return False, f"Failed to open {key}: {e}"

    try:
        os.startfile(app_name)
        return True, f"Launched {app_name}."
    except Exception as exc:
        return False, f"Failed to launch {app_name}: {exc}"


# Alias for backward compatibility
launch_app = open_application


def control_spotify(action: str, query: str = "") -> Tuple[bool, str]:
    """Control Spotify playback or search for songs/artists."""
    act = action.strip().lower()
    try:
        if act == "playpause":
            pyautogui.press("playpause")
            return True, "Spotify playback toggled."
        elif act in ["next", "shuffle"]:
            pyautogui.press("nexttrack")
            return True, "Skipped to next track on Spotify."
        elif act == "search":
            encoded_query = urllib.parse.quote(query.strip())
            os.system(f"start spotify:search:{encoded_query}")
            return True, f"Searching Spotify for {query}."
        else:
            return False, f"Unknown Spotify action: {action}"
    except Exception as exc:
        return False, f"Failed to control Spotify: {exc}"


# Tool Schemas for Ollama / LLM Function Calling
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "control_spotify",
            "description": "Control Spotify music playback (play, pause, next track, shuffle) or search for songs/artists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["playpause", "next", "shuffle", "search"],
                        "description": "Action to perform: 'playpause', 'next', 'shuffle', or 'search'."
                    },
                    "query": {
                        "type": "string",
                        "description": "Search term for songs, artists, or albums when action is 'search'."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Retrieve computer hardware stats including CPU, memory, disk, and battery.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launch desktop applications such as Notepad, Calculator, Spotify, or Antigravity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to open."
                    }
                },
                "required": ["app_name"]
            }
        }
    }
]


def handle_system_command(text: str) -> Tuple[bool, str]:
    """Inspect text for system and Spotify commands and execute them if recognized."""
    lower_text = text.strip().lower()

    # System stats keywords
    stats_triggers = [
        "system status",
        "system stats",
        "system health",
        "cpu usage",
        "memory usage",
        "ram usage",
        "how is the system",
        "system specifications",
        "system info",
    ]
    if any(trigger in lower_text for trigger in stats_triggers):
        stats = get_system_stats()
        return True, stats["summary"]

    # Spotify Play/Pause keywords
    playpause_triggers = [
        "pause music", "stop music", "resume music", "play music",
        "pause song", "stop song", "play song", "toggle playback",
        "pause", "resume"
    ]
    if lower_text in playpause_triggers or any(lower_text == t for t in playpause_triggers):
        return control_spotify("playpause")

    # Spotify Next/Shuffle keywords
    next_triggers = ["next track", "next song", "skip song", "skip track", "next", "shuffle music", "shuffle playlist", "shuffle"]
    if lower_text in next_triggers or any(t in lower_text for t in ["next song", "next track", "skip track", "skip song", "shuffle"]):
        return control_spotify("next")

    # Spotify search / play artist keywords
    search_prefixes = [
        "search for ", "search spotify for ", "play on spotify ", "play the song ",
        "play artist ", "play "
    ]
    for prefix in search_prefixes:
        if lower_text.startswith(prefix):
            query = lower_text[len(prefix):].strip()
            # If query is not empty and not just 'music'
            if query and query not in ["music", "song"]:
                return control_spotify("search", query=query)

    # App launching keywords
    launch_triggers = ["open", "launch", "start", "run"]
    for trigger in launch_triggers:
        if trigger in lower_text:
            apps_keywords = ["spotify", "spot if", "notepad", "calculator", "calc", "antigravity"]
            for app in apps_keywords:
                if app in lower_text:
                    success, msg = open_application(app)
                    return True, msg

    return False, ""


if __name__ == "__main__":
    print("Testing system stats:")
    stats = get_system_stats()
    print(stats["summary"])
    print("\nTesting Spotify search control:")
    success, msg = control_spotify("search", query="The Weeknd")
    print(success, msg)
