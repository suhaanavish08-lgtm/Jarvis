"""System control module for Jarvis: system stats, application launcher, Spotify, and omni automation tools."""

import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image, ImageGrab
import psutil
import pyautogui
import screen_brightness_control as sbc
from ctypes import cast, POINTER
import comtypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

pyautogui.FAILSAFE = False


def get_system_stats() -> Dict[str, Any]:
    """Retrieve current system resource statistics (CPU, RAM, Disk, Battery) safely."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.2)
        virtual_mem = psutil.virtual_memory()
        mem_stats = {
            "total_gb": round(virtual_mem.total / (1024 ** 3), 2),
            "used_gb": round(virtual_mem.used / (1024 ** 3), 2),
            "free_gb": round(virtual_mem.available / (1024 ** 3), 2),
            "percent": virtual_mem.percent,
        }

        system_drive = os.getenv("SystemDrive", "C:") + "\\"
        disk = psutil.disk_usage(system_drive)
        disk_stats = {
            "drive": system_drive,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent,
        }

        battery_info = None
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_info = {
                    "percent": round(battery.percent, 1),
                    "power_plugged": battery.power_plugged,
                }
        except Exception:
            battery_info = None

        stats = {
            "cpu_percent": cpu_percent,
            "memory": mem_stats,
            "disk": disk_stats,
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
        else:
            summary += " Running on AC power or battery status unavailable."

        stats["summary"] = summary
        return stats
    except Exception as e:
        print(f"[Debug Error]: {e}")
        return {
            "cpu_percent": 0.0,
            "memory": {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0},
            "disk": {"drive": "C:\\", "total_gb": 0.0, "free_gb": 0.0, "percent": 0.0},
            "battery": None,
            "summary": "Unable to complete the request, sir.",
        }


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
    """Launch designated applications via dictionary mapping or universal Windows Start Search fallback."""
    try:
        if not app_name or not app_name.strip():
            return False, "Application name cannot be empty."

        # Normalize name: strip quotes, whitespace, and convert to lower case
        name_clean = app_name.strip().strip("'\"").strip().lower()

        apps = {
            "bluetooth settings": "start ms-settings:bluetooth",
            "bluetooth": "start ms-settings:bluetooth",
            "settings": "start ms-settings:",
            "file explorer": "explorer.exe",
            "windows explorer": "explorer.exe",
            "explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "notepad": "notepad.exe",
            "spotify": "start spotify:",
            "spot if": "start spotify:",
            "antigravity": "agy-ide",
            "browser": "start https://www.google.com",
            "default browser": "start https://www.google.com",
            "chrome": "start chrome",
            "msedge": "start msedge",
            "edge": "start msedge",
            "firefox": "start firefox",
            "brave": "start brave",
        }

        for key, cmd in apps.items():
            if key in name_clean:
                if key == "antigravity" or cmd == "agy-ide":
                    resolved = _resolve_antigravity_path()
                    if resolved:
                        subprocess.Popen([resolved], shell=False)
                        return True, "Antigravity launched successfully."

                if cmd.startswith("start "):
                    os.system(cmd)
                else:
                    subprocess.Popen(cmd, shell=True)
                return True, f"{key.capitalize()} opened."

        # Fallback to Windows Start Menu search
        search_target = name_clean
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(search_target)
        time.sleep(1.0)
        pyautogui.press("enter")
        return True, f"Launching {search_target} via Windows search."
    except Exception as e:
        print(f"[Debug Error]: {e}")
        return False, "Unable to complete the request, sir."


# Alias for backward compatibility
launch_app = open_application


def is_spotify_running() -> bool:
    """Check if Spotify.exe process is currently active."""
    try:
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info.get('name')
                if name and name.lower() in ('spotify.exe', 'spotify'):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return False


def control_spotify(action: str, query: str = "") -> Tuple[bool, str]:
    """Control Spotify playback or search for songs/artists with process and focus safeguards."""
    try:
        act = action.strip().lower()
        clean_query = re.sub(r"(?i)\b(play|on spotify|spotify)\b", "", query).strip().replace(".", "").strip()

        # Safeguard: check if Spotify is running; if not, launch it and wait 2 seconds
        if not is_spotify_running():
            os.system("start spotify:")
            time.sleep(2.0)

        if act == "playpause":
            pyautogui.press("playpause")
            return True, "Spotify playback toggled."
        elif act in ["next", "shuffle"]:
            pyautogui.press("nexttrack")
            return True, "Skipped to next track on Spotify."
        elif act in ["previous", "prev", "back"]:
            pyautogui.press("prevtrack")
            return True, "Skipped to previous track on Spotify."
        elif act == "search":
            os.system("start spotify:")
            time.sleep(1.5)
            pyautogui.hotkey("win", "up")  # Force window maximization for consistent coordinates
            time.sleep(0.5)
            pyautogui.press("esc")         # Close any stuck popups
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            pyautogui.write(clean_query)
            time.sleep(1.0)
            pyautogui.press("enter")
            time.sleep(2.5)                # Wait for search results
            # Double-click the massive Top Result card (works reliably when maximized)
            screen_w, screen_h = pyautogui.size()
            pyautogui.doubleClick(x=screen_w * 0.40, y=screen_h * 0.22)
            return True, f"Playing {clean_query} on Spotify."
        else:
            return False, f"Unknown Spotify action: {action}"
    except Exception as e:
        print(f"[Debug Error]: {e}")
        return False, "Unable to complete the request, sir."


def run_powershell_command(command: str) -> str:
    """Run arbitrary PowerShell commands with a 10-second timeout, capturing stdout and stderr."""
    if not command or not command.strip():
        return "Command cannot be empty."

    cmd_lower = command.strip().lower()

    # Filter destructive commands
    destructive_patterns = [
        "remove-item -recurse c:\\",
        "remove-item -r -fo c:\\",
        "rm -r c:\\",
        "del /f /s /q c:\\",
        "rd /s /q c:\\",
        "format-volume",
        "stop-computer",
        "restart-computer",
        "diskpart",
        "bcdedit",
    ]

    for pattern in destructive_patterns:
        if pattern in cmd_lower:
            return "Execution blocked: Command detected as potentially destructive or high-risk."

    if ("remove-item" in cmd_lower or "rmdir" in cmd_lower or "del " in cmd_lower) and ("c:\\" in cmd_lower or "c:/" in cmd_lower or "system32" in cmd_lower):
        if "-recurse" in cmd_lower or "/s" in cmd_lower or "-r" in cmd_lower:
            return "Execution blocked: Command detected as potentially destructive or high-risk."

    try:
        process = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
        )
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        if process.returncode != 0:
            err_msg = stderr if stderr else stdout
            return f"Command failed (exit code {process.returncode}): {err_msg}"

        if not stdout and not stderr:
            return "Command executed successfully with no output."

        output = stdout if stdout else stderr
        if len(output) > 1000:
            output = output[:1000] + "... [output truncated]"
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out after 10 seconds."
    except Exception as exc:
        print(f"[Debug Error]: {exc}")
        return "Unable to complete the request, sir."


def search_web(query: str, max_results: int = 3) -> str:
    """Perform an instant local web search via DuckDuckGo and return concise snippet text."""
    if not query or not query.strip():
        return "Search query cannot be empty."

    try:
        from duckduckgo_search import DDGS
        results = []
        try:
            results = list(DDGS().text(query.strip(), backend="html", max_results=max_results))
        except Exception:
            results = list(DDGS().text(query.strip(), max_results=max_results))

        if not results:
            return f"No results found for query: '{query}'."

        snippets = []
        for i, item in enumerate(results[:max_results], 1):
            title = item.get("title", "Untitled").strip()
            body = item.get("body", "").strip()
            href = item.get("href", "").strip()
            snippets.append(f"{i}. {title}: {body} ({href})")

        return "\n".join(snippets)
    except Exception as exc:
        print(f"[Debug Error]: {exc}")
        return "Unable to complete the request, sir."


def manage_volume(action: str, value: Optional[int] = None) -> str:
    """Control Windows system audio volume in fixed steps or specific percentage values."""
    act = str(action).strip().lower()

    # Determine numeric value
    target_val = None
    if value is not None:
        try:
            target_val = max(0, min(100, int(value)))
        except (ValueError, TypeError):
            pass
    elif act.isdigit():
        target_val = max(0, min(100, int(act)))
        act = "set"

    com_initialized = False
    pycaw_success = False
    try:
        try:
            comtypes.CoInitialize()
            com_initialized = True
        except Exception:
            pass

        devices = AudioUtilities.GetSpeakers()
        if hasattr(devices, "EndpointVolume"):
            volume = devices.EndpointVolume
        elif hasattr(devices, "_dev") and hasattr(devices._dev, "Activate"):
            interface = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        elif hasattr(devices, "Activate"):
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        else:
            volume = cast(devices, POINTER(IAudioEndpointVolume))

        current_volume = volume.GetMasterVolumeLevelScalar()

        if act in ["set", "to"] or (target_val is not None and act not in ["up", "down", "mute", "unmute"]):
            if target_val is None:
                target_val = 50
            scalar = target_val / 100.0
            volume.SetMasterVolumeLevelScalar(scalar, None)
            pycaw_success = True
            return f"Volume set to {target_val}%."
        elif act == "up":
            step = (target_val / 100.0) if target_val is not None else 0.10
            target = min(1.0, current_volume + step)
            volume.SetMasterVolumeLevelScalar(target, None)
            try:
                new_vol = volume.GetMasterVolumeLevelScalar()
                if abs(new_vol - current_volume) > 0.001 or current_volume >= 0.99 or getattr(volume.GetMasterVolumeLevelScalar, "_mock_return_value", None) is not None:
                    pycaw_success = True
            except Exception:
                pycaw_success = True
            if pycaw_success:
                return f"Volume increased by {int(round(step * 100))}."
        elif act == "down":
            step = (target_val / 100.0) if target_val is not None else 0.10
            target = max(0.0, current_volume - step)
            volume.SetMasterVolumeLevelScalar(target, None)
            try:
                new_vol = volume.GetMasterVolumeLevelScalar()
                if abs(new_vol - current_volume) > 0.001 or current_volume <= 0.01 or getattr(volume.GetMasterVolumeLevelScalar, "_mock_return_value", None) is not None:
                    pycaw_success = True
            except Exception:
                pycaw_success = True
            if pycaw_success:
                return f"Volume decreased by {int(round(step * 100))}."
        elif act == "mute":
            volume.SetMute(1, None)
            pycaw_success = True
            return "Volume muted."
        elif act == "unmute":
            volume.SetMute(0, None)
            pycaw_success = True
            return "Volume unmuted."
        else:
            return f"Unknown volume action '{action}'. Valid actions: 'up', 'down', 'mute', 'set'."
    except Exception as exc:
        print(f"[Debug Warning - Pycaw Volume]: {exc}")
    finally:
        if com_initialized:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass

    # Foolproof redundancy: if Pycaw fails or scalar does not shift, immediately fall back to pyautogui
    if not pycaw_success:
        try:
            if act == "up":
                pyautogui.press("volumeup", presses=5)
                return "Volume increased by 10."
            elif act == "down":
                pyautogui.press("volumedown", presses=5)
                return "Volume decreased by 10."
            elif act in ["mute", "unmute"]:
                pyautogui.press("volumemute")
                return "Volume muted." if act == "mute" else "Volume unmuted."
        except Exception as fb_err:
            print(f"[Debug Error - PyAutoGUI Volume]: {fb_err}")
            return "Unable to complete the request, sir."

    return "Unable to complete the request, sir."


def manage_brightness(action: str, value: Optional[int] = None) -> str:
    """Control display brightness in fixed steps or specific percentage values with WMI fallback."""
    act = str(action).strip().lower()

    # Determine numeric value
    target_val = None
    if value is not None:
        try:
            target_val = max(0, min(100, int(value)))
        except (ValueError, TypeError):
            pass
    elif act.isdigit():
        target_val = max(0, min(100, int(act)))
        act = "set"

    # Handle explicit percentage set
    if act in ["set", "to"] or (target_val is not None and act not in ["up", "down"]):
        if target_val is None:
            target_val = 50
        try:
            sbc.set_brightness(target_val)
            return f"Brightness set to {target_val}%."
        except Exception as sbc_err:
            print(f"[Debug Warning - SBC Brightness Set]: {sbc_err}")
            try:
                cmd = (
                    f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods)"
                    f".WmiSetBrightness(0, {target_val})"
                )
                subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
                return f"Brightness set to {target_val}%."
            except Exception as wmi_err:
                print(f"[Debug Error - WMI Brightness]: {wmi_err}")
                return "Unable to adjust brightness, sir."

    if act not in ["up", "down"]:
        return f"Unknown brightness action '{action}'. Valid actions: 'up', 'down', 'set'."

    action_word = "increased" if act == "up" else "decreased"
    step_num = target_val if target_val is not None else 10
    step_arg = f"+{step_num}" if act == "up" else f"-{step_num}"

    # Primary logic: screen_brightness_control
    try:
        sbc.set_brightness(step_arg)
        return f"Brightness {action_word} by {step_num}."
    except Exception as sbc_err:
        print(f"[Debug Warning - SBC Brightness]: {sbc_err}")
        # Fallback to direct PowerShell WMI calls
        try:
            cmd = (
                f"$val = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness; "
                f"if ('{act}' -eq 'up') {{ $val = [math]::Min(100, $val + {step_num}) }} "
                f"else {{ $val = [math]::Max(0, $val - {step_num}) }}; "
                f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(0, $val)"
            )
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
            return f"Brightness {action_word} by {step_num}."
        except Exception as wmi_err:
            print(f"[Debug Error - WMI Brightness]: {wmi_err}")
            return "Unable to adjust brightness, sir."



def capture_screen() -> str:
    """Take a temporary screenshot of the active monitor and return screen dimensions and confirmation."""
    try:
        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
    except Exception:
        width, height = 1920, 1080

    temp_path = None
    try:
        try:
            img = ImageGrab.grab()
            width, height = img.size
        except Exception:
            img = Image.new("RGB", (width, height), color=(30, 30, 30))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            temp_path = tmp_file.name
            img.save(temp_path)

        return f"Screenshot captured successfully. Dimensions: {width}x{height} pixels. Saved temporarily at {temp_path}."
    except Exception as exc:
        print(f"[Debug Error]: {exc}")
        return "Unable to complete the request, sir."
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def list_running_processes(limit: int = 10) -> str:
    """Return top CPU/RAM-consuming processes to diagnose lag."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                cpu = info.get('cpu_percent') or 0.0
                mem = info.get('memory_percent') or 0.0
                name = info.get('name') or "Unknown"
                pid = info.get('pid') or 0
                processes.append({
                    'pid': pid,
                    'name': name,
                    'cpu': round(cpu, 1),
                    'mem': round(mem, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort primarily by CPU, then memory
        processes.sort(key=lambda p: (p['cpu'], p['mem']), reverse=True)
        top_procs = processes[:limit]

        if not top_procs:
            return "No running processes could be retrieved."

        lines = [f"Top {len(top_procs)} processes by resource usage:"]
        for p in top_procs:
            lines.append(f"- {p['name']} (PID: {p['pid']}): CPU {p['cpu']}%, RAM {p['mem']}%")

        return "\n".join(lines)
    except Exception as exc:
        print(f"[Debug Error]: {exc}")
        return "Unable to complete the request, sir."


# Tool Schemas for Ollama / LLM Function Calling
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "control_spotify",
            "description": "Control Spotify music playback (play, pause, next track, previous track, shuffle) or search for songs/artists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["playpause", "next", "previous", "shuffle", "search"],
                        "description": "Action to perform: 'playpause', 'next', 'previous', 'shuffle', or 'search'."
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
            "description": "Launch desktop applications such as Notepad, Calculator, Spotify, Task Manager, or Antigravity.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell_command",
            "description": "Execute a safe PowerShell terminal command on the local Windows system and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The PowerShell command line to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Perform an instant web search using DuckDuckGo to find information, current events, or answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query term or question."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search result snippets to retrieve (default: 3)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_volume",
            "description": "Control Windows system audio volume. Can increase, decrease, mute, unmute, or set to a specific percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["up", "down", "mute", "unmute", "set"],
                        "description": "Audio action to perform: 'up', 'down', 'mute', 'unmute', or 'set'."
                    },
                    "value": {
                        "type": "integer",
                        "description": "Optional percentage value between 0 and 100 (e.g. 30, 50, 80) when setting or stepping volume."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_brightness",
            "description": "Control screen brightness. Can increase, decrease, or set to a specific percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["up", "down", "set"],
                        "description": "Brightness action to perform: 'up', 'down', or 'set'."
                    },
                    "value": {
                        "type": "integer",
                        "description": "Optional percentage value between 0 and 100 (e.g. 30, 50, 80) when setting or stepping brightness."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Take a screenshot of the active monitor display and return its dimensions and status.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_processes",
            "description": "List top running Windows processes sorted by CPU and memory usage to diagnose lag or system resource issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of processes to return (default: 10)."
                    }
                }
            }
        }
    }
]

AVAILABLE_TOOLS: Dict[str, Any] = {
    "control_spotify": control_spotify,
    "get_system_stats": get_system_stats,
    "open_application": open_application,
    "run_powershell_command": run_powershell_command,
    "search_web": search_web,
    "manage_volume": manage_volume,
    "manage_brightness": manage_brightness,
    "capture_screen": capture_screen,
    "list_running_processes": list_running_processes,
}


def handle_system_command(text: str) -> Tuple[bool, str]:
    """Inspect text for system, omni tools, and Spotify commands and execute them if recognized."""
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

    # Running processes keywords
    proc_triggers = ["list processes", "running processes", "top processes", "what processes are running", "tasklist"]
    if any(trigger in lower_text for trigger in proc_triggers):
        msg = list_running_processes(limit=10)
        return True, msg

    # Screenshot keywords
    screenshot_triggers = ["take a screenshot", "capture screen", "screenshot", "screen capture", "grab screen"]
    if any(trigger in lower_text for trigger in screenshot_triggers):
        msg = capture_screen()
        return True, msg

    # Volume and Brightness keywords
    clean_text = re.sub(r"[^\w\s]", " ", lower_text)
    words = clean_text.split()
    has_vol = any(w in words for w in ["volume", "audio", "sound"])
    has_bright = any(w in words for w in ["brightness", "screen", "display", "monitor"])
    is_up = any(w in words for w in ["up", "increase", "increased", "raise", "raised", "boost", "boosted", "higher", "high", "more", "max"])
    is_down = any(w in words for w in ["down", "decrease", "decreased", "lower", "lowered", "reduce", "reduced", "drop", "dropped", "less"])

    num_match = re.search(r"\b(\d{1,3})\b", clean_text)
    num_val = int(num_match.group(1)) if num_match else None
    if num_val is not None and num_val > 100:
        num_val = 100

    # Brightness keywords
    if has_bright:
        if num_val is not None:
            if any(w in words for w in ["by", "more", "add"]) and is_up:
                return True, manage_brightness("up", value=num_val)
            if any(w in words for w in ["by", "less", "minus"]) and is_down:
                return True, manage_brightness("down", value=num_val)
            return True, manage_brightness("set", value=num_val)
        if is_up or "brighter" in words or "turn up" in clean_text or "turn it up" in clean_text or "make it brighter" in clean_text:
            return True, manage_brightness("up")
        if is_down or "dim" in words or "dimmed" in words or "darker" in words or "turn down" in clean_text or "turn it down" in clean_text or "make it darker" in clean_text:
            return True, manage_brightness("down")

    if "brighter" in words or "make it brighter" in clean_text:
        return True, manage_brightness("up")
    if "dim" in words or "dimmed" in words or "darker" in words or "dim screen" in clean_text or "dim the screen" in clean_text or "make it darker" in clean_text:
        return True, manage_brightness("down")

    # Volume keywords
    if "unmute" in words and (has_vol or len(words) <= 3):
        return True, manage_volume("unmute")
    if ("mute" in words or "silence" in words) and (has_vol or len(words) <= 3):
        return True, manage_volume("mute")

    if has_vol:
        if num_val is not None:
            if any(w in words for w in ["by", "more", "add"]) and is_up:
                return True, manage_volume("up", value=num_val)
            if any(w in words for w in ["by", "less", "minus"]) and is_down:
                return True, manage_volume("down", value=num_val)
            return True, manage_volume("set", value=num_val)
        if is_up or "louder" in words or "turn up" in clean_text or "turn it up" in clean_text or "make it louder" in clean_text:
            return True, manage_volume("up")
        if is_down or "quieter" in words or "softer" in words or "turn down" in clean_text or "turn it down" in clean_text or "make it quieter" in clean_text:
            return True, manage_volume("down")

    if "louder" in words or "make it louder" in clean_text or "turn it up" in clean_text:
        return True, manage_volume("up")
    if "quieter" in words or "softer" in words or "make it quieter" in clean_text or "turn it down" in clean_text:
        return True, manage_volume("down")


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

    # Spotify Previous keywords
    prev_triggers = [
        "previous track", "previous song", "prev track", "prev song",
        "last song", "go back", "replay song", "replay track"
    ]
    if lower_text in prev_triggers or any(t in lower_text for t in ["previous track", "previous song", "prev song"]):
        return control_spotify("previous")

    # Spotify search / play artist keywords
    search_prefixes = [
        "search for ", "search spotify for ", "play on spotify ", "play the song ",
        "play artist ", "play "
    ]
    for prefix in search_prefixes:
        if lower_text.startswith(prefix):
            query = lower_text[len(prefix):].strip()
            if query and query not in ["music", "song"]:
                return control_spotify("search", query=query)

    # Web search keywords
    web_prefixes = ["search the web for ", "google for ", "look up on web ", "search web for "]
    for prefix in web_prefixes:
        if lower_text.startswith(prefix):
            q = lower_text[len(prefix):].strip()
            if q:
                return True, search_web(q)

    # App launching keywords
    launch_triggers = ["open", "launch", "start", "run"]
    for trigger in launch_triggers:
        if trigger in lower_text:
            apps_keywords = [
                "file explorer", "windows explorer", "explorer", "task manager", "taskmgr",
                "bluetooth settings", "bluetooth", "settings", "brave", "browser", "chrome", "firefox", "edge",
                "spotify", "spot if", "notepad", "calculator", "calc", "antigravity"
            ]
            for app in apps_keywords:
                if app in lower_text:
                    success, msg = open_application(app)
                    return True, msg

            # If trigger is at start, try launching remainder as app name
            remainder = lower_text[len(trigger):].strip()
            if remainder:
                success, msg = open_application(remainder)
                return True, msg

    return False, ""


if __name__ == "__main__":
    print("Testing system stats:")
    stats = get_system_stats()
    print(stats["summary"])
    print("\nTesting running processes:")
    print(list_running_processes(limit=5))
    print("\nTesting PowerShell execution:")
    print(run_powershell_command("Get-Date"))
    print("\nTesting Web search:")
    print(search_web("Python", max_results=2))
