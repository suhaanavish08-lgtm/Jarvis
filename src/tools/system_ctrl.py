"""System control module for Jarvis: system stats and application launcher."""

import os
import shutil
import subprocess
import sys
from typing import Dict, Any, Tuple
import psutil


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
    
    # Build concise human-readable summary for voice output
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
    # Check PATH first
    agy_cmd = shutil.which("antigravity") or shutil.which("antigravity-ide") or shutil.which("agy")
    if agy_cmd:
        return agy_cmd

    # Check common user install paths on Windows
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


def handle_system_command(text: str) -> Tuple[bool, str]:
    """Inspect text for system commands and execute them if recognized."""
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

    # App launching keywords
    launch_triggers = ["open", "launch", "start", "run"]
    for trigger in launch_triggers:
        if trigger in lower_text:
            apps_keywords = ["spotify", "notepad", "calculator", "calc", "antigravity"]
            for app in apps_keywords:
                if app in lower_text:
                    success, msg = open_application(app)
                    return True, msg

    return False, ""


if __name__ == "__main__":
    print("Testing system stats:")
    stats = get_system_stats()
    print(stats["summary"])
    print("\nTesting Spotify launcher definition:")
    res, msg = open_application("spotify")
    print(res, msg)
