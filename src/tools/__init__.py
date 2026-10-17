"""Jarvis tools package."""
from .system_ctrl import (
    get_system_stats,
    launch_app,
    open_application,
    control_spotify,
    is_spotify_running,
    run_powershell_command,
    search_web,
    manage_volume,
    manage_brightness,
    capture_screen,
    list_running_processes,
    handle_system_command,
    TOOL_SCHEMAS,
    AVAILABLE_TOOLS,
)

__all__ = [
    "get_system_stats",
    "launch_app",
    "open_application",
    "control_spotify",
    "is_spotify_running",
    "run_powershell_command",
    "search_web",
    "manage_volume",
    "manage_brightness",
    "capture_screen",
    "list_running_processes",
    "handle_system_command",
    "TOOL_SCHEMAS",
    "AVAILABLE_TOOLS",
]
