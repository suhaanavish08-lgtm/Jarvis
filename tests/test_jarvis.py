"""Comprehensive automated test harness for Jarvis local AI voice assistant."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call
import numpy as np

# Ensure src directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from tools.system_ctrl import (
    get_system_stats,
    open_application,
    launch_app,
    control_spotify,
    is_spotify_running,
    handle_system_command,
    TOOL_SCHEMAS,
)
import main
from main import (
    chunk_text,
    synthesize_speech,
    speak,
    VoiceAssistant,
    MODELS_DIR,
    KOKORO_MODEL_FILE,
    KOKORO_VOICES_FILE,
)


class TestSystemStats(unittest.TestCase):
    """Test get_system_stats for metric accuracy, safe returns, and permission handling."""

    def test_get_system_stats_returns_valid_metrics(self):
        stats = get_system_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("cpu_percent", stats)
        self.assertIn("memory", stats)
        self.assertIn("disk", stats)
        self.assertIn("battery", stats)
        self.assertIn("summary", stats)

        # Check types and non-empty summary
        self.assertIsInstance(stats["cpu_percent"], (int, float))
        self.assertIsInstance(stats["memory"]["percent"], (int, float))
        self.assertIsInstance(stats["disk"]["total_gb"], (int, float))
        self.assertIsInstance(stats["summary"], str)
        self.assertTrue(len(stats["summary"].strip()) > 0)
        self.assertIn("CPU is running at", stats["summary"])

    @patch("psutil.cpu_percent", side_effect=PermissionError("CPU access denied"))
    @patch("psutil.virtual_memory", side_effect=PermissionError("RAM access denied"))
    @patch("psutil.disk_usage", side_effect=PermissionError("Disk access denied"))
    def test_get_system_stats_permission_exceptions_handled_safely(self, mock_disk, mock_mem, mock_cpu):
        # Ensure that even with total OS permission denial, no exception is raised
        stats = get_system_stats()
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["cpu_percent"], 0.0)
        self.assertEqual(stats["memory"]["percent"], 0.0)
        self.assertTrue(len(stats["summary"]) > 0)

    @patch("psutil.sensors_battery", return_value=None)
    def test_get_system_stats_without_battery(self, mock_battery):
        stats = get_system_stats()
        self.assertIsNone(stats["battery"])
        self.assertIn("battery status unavailable", stats["summary"].lower())


class TestAppLaunching(unittest.TestCase):
    """Test open_application for explicit targets, input sanitization, and fallback resilience."""

    @patch("os.system")
    @patch("subprocess.Popen")
    def test_explicit_targets_settings(self, mock_popen, mock_os_system):
        success, msg = open_application("settings")
        self.assertTrue(success)
        mock_os_system.assert_called_with("start ms-settings:")
        self.assertIn("Settings opened", msg)

    @patch("subprocess.Popen")
    def test_explicit_targets_file_explorer(self, mock_popen):
        success, msg = open_application("file explorer")
        self.assertTrue(success)
        mock_popen.assert_called_with("explorer.exe", shell=True)
        self.assertIn("File explorer opened", msg)

    @patch("subprocess.Popen")
    def test_explicit_targets_task_manager(self, mock_popen):
        success, msg = open_application("task manager")
        self.assertTrue(success)
        mock_popen.assert_called_with("taskmgr.exe", shell=True)
        self.assertIn("Task manager opened", msg)

    @patch("subprocess.Popen")
    def test_explicit_targets_calculator(self, mock_popen):
        success, msg = open_application("calculator")
        self.assertTrue(success)
        mock_popen.assert_called_with("calc.exe", shell=True)
        self.assertIn("Calculator opened", msg)

    @patch("os.system")
    def test_explicit_targets_default_browser(self, mock_os_system):
        success, msg = open_application("browser")
        self.assertTrue(success)
        mock_os_system.assert_called_with("start https://www.google.com")
        self.assertIn("Browser opened", msg)

    @patch("os.system")
    def test_input_normalization_quotes_and_spaces(self, mock_os_system):
        success, msg = open_application('   "Settings"   ')
        self.assertTrue(success)
        mock_os_system.assert_called_with("start ms-settings:")

    def test_empty_app_name_rejected(self):
        success, msg = open_application("   ")
        self.assertFalse(success)
        self.assertIn("Application name cannot be empty", msg)

    @patch("pyautogui.press")
    @patch("pyautogui.write")
    @patch("time.sleep")
    def test_windows_search_fallback(self, mock_sleep, mock_write, mock_press):
        success, msg = open_application("unregistered_utility_app")
        self.assertTrue(success)
        mock_press.assert_has_calls([call("win"), call("enter")])
        mock_write.assert_called_with("unregistered_utility_app")
        self.assertIn("Launching unregistered_utility_app via Windows search", msg)

    @patch("pyautogui.press", side_effect=OSError(2, "WinError 2: File not found"))
    def test_windows_search_fallback_winerror_resilience(self, mock_press):
        success, msg = open_application("nonexistent_binary")
        self.assertFalse(success)
        self.assertIn("Failed to launch nonexistent_binary", msg)


class TestSpotifyControls(unittest.TestCase):
    """Test control_spotify actions, running safeguards, and search focus handling."""

    @patch("tools.system_ctrl.is_spotify_running", return_value=True)
    @patch("pyautogui.press")
    def test_spotify_playpause_action(self, mock_press, mock_running):
        success, msg = control_spotify("playpause")
        self.assertTrue(success)
        mock_press.assert_called_with("playpause")
        self.assertIn("toggled", msg)

    @patch("tools.system_ctrl.is_spotify_running", return_value=True)
    @patch("pyautogui.press")
    def test_spotify_next_action(self, mock_press, mock_running):
        success, msg = control_spotify("next")
        self.assertTrue(success)
        mock_press.assert_called_with("nexttrack")
        self.assertIn("Skipped to next track", msg)

    @patch("tools.system_ctrl.is_spotify_running", return_value=True)
    @patch("pyautogui.press")
    def test_spotify_previous_action(self, mock_press, mock_running):
        success, msg = control_spotify("previous")
        self.assertTrue(success)
        mock_press.assert_called_with("prevtrack")
        self.assertIn("Skipped to previous track", msg)

    @patch("tools.system_ctrl.is_spotify_running", return_value=False)
    @patch("os.system")
    @patch("time.sleep")
    @patch("pyautogui.press")
    def test_spotify_safeguard_launches_when_not_running(self, mock_press, mock_sleep, mock_os_system, mock_running):
        success, msg = control_spotify("playpause")
        self.assertTrue(success)
        # Should launch Spotify and wait 2 seconds first
        mock_os_system.assert_called_with("start spotify:")
        mock_sleep.assert_any_call(2.0)
        mock_press.assert_called_with("playpause")

    @patch("tools.system_ctrl.is_spotify_running", return_value=True)
    @patch("os.system")
    @patch("time.sleep")
    @patch("pyautogui.hotkey")
    @patch("pyautogui.write")
    @patch("pyautogui.press")
    def test_spotify_search_focus_and_keystrokes(self, mock_press, mock_write, mock_hotkey, mock_sleep, mock_os_system, mock_running):
        success, msg = control_spotify("search", query="The Hills")
        self.assertTrue(success)
        # Verify focus is ensured via start spotify:
        mock_os_system.assert_called_with("start spotify:")
        # Verify keystrokes
        mock_hotkey.assert_called_with("ctrl", "l")
        mock_write.assert_called_with("The Hills")
        # Verify navigation tabs and play enter
        tab_calls = [c for c in mock_press.call_args_list if c == call("tab")]
        self.assertEqual(len(tab_calls), 3)
        self.assertIn("Playing The Hills on Spotify", msg)

    def test_spotify_unknown_action(self):
        with patch("tools.system_ctrl.is_spotify_running", return_value=True):
            success, msg = control_spotify("invalid_action")
            self.assertFalse(success)
            self.assertIn("Unknown Spotify action", msg)


class TestKokoroTTSEngine(unittest.TestCase):
    """Test Kokoro TTS models presence, sentence chunking, and smooth speech synthesis."""

    def test_models_exist_and_loaded(self):
        model_path = os.path.join(MODELS_DIR, KOKORO_MODEL_FILE)
        voices_path = os.path.join(MODELS_DIR, KOKORO_VOICES_FILE)
        self.assertTrue(os.path.exists(model_path), f"Missing Kokoro model at {model_path}")
        self.assertTrue(os.path.exists(voices_path), f"Missing Kokoro voices at {voices_path}")
        self.assertIsNotNone(main.kokoro)

    def test_chunk_text_delimiters(self):
        text = "Good morning, sir. All systems are operational; CPU load is 14%. Shall I bring up the diagnostics?"
        chunks = chunk_text(text, max_chunk_chars=50)
        self.assertTrue(len(chunks) >= 2)
        # Verify content was preserved
        combined_text = " ".join(chunks)
        self.assertIn("Good morning, sir.", combined_text)
        self.assertIn("operational;", combined_text)
        self.assertIn("diagnostics?", combined_text)

    def test_chunk_text_empty_input(self):
        chunks = chunk_text("   \n\t  ")
        self.assertEqual(chunks, [])

    def test_smooth_speech_synthesis(self):
        sample_phrase = "Good day, sir. All core protocols are functioning within nominal parameters."
        audio_array, sr = synthesize_speech(sample_phrase, voice="bm_daniel", speed=1.1)
        self.assertIsNotNone(audio_array)
        self.assertIsInstance(audio_array, np.ndarray)
        self.assertTrue(len(audio_array) > 0)
        self.assertEqual(sr, 24000)

    @patch("sounddevice.play")
    @patch("sounddevice.wait")
    def test_speak_invocation(self, mock_wait, mock_play):
        speak("At your service, sir.")
        mock_play.assert_called_once()
        mock_wait.assert_called_once()


class TestLLMToolCalling(unittest.TestCase):
    """Test LLM tool-calling simulation with Ollama: argument parsing, execution, and history recording."""

    def setUp(self):
        self.assistant = VoiceAssistant(model_name="jarvis", voice="bm_daniel")

    @patch("ollama.chat")
    def test_tool_calling_system_stats(self, mock_ollama_chat):
        # Simulate Ollama tool call response
        mock_ollama_chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_system_stats",
                            "arguments": {}
                        }
                    }
                ]
            }
        }

        reply = self.assistant.query_ollama("Check system health")
        self.assertIn("Certainly, sir", reply)
        self.assertIn("CPU is running at", reply)
        # Check history fed back
        last_history = self.assistant.conversation_history[-1]
        self.assertEqual(last_history["role"], "assistant")
        self.assertIn("CPU is running at", last_history["content"])

    @patch("ollama.chat")
    @patch("tools.system_ctrl.is_spotify_running", return_value=True)
    @patch("pyautogui.press")
    def test_tool_calling_spotify_json_string_arguments(self, mock_press, mock_running, mock_ollama_chat):
        # Simulate tool call with arguments as a JSON string instead of dict
        mock_ollama_chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "control_spotify",
                            "arguments": '{"action": "previous"}'
                        }
                    }
                ]
            }
        }

        reply = self.assistant.query_ollama("Play previous song")
        self.assertIn("Certainly, sir", reply)
        self.assertIn("Skipped to previous track on Spotify", reply)
        mock_press.assert_called_with("prevtrack")

    @patch("ollama.chat")
    @patch("subprocess.Popen")
    def test_tool_calling_open_application(self, mock_popen, mock_ollama_chat):
        mock_ollama_chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "open_application",
                            "arguments": {"app_name": "task manager"}
                        }
                    }
                ]
            }
        }

        reply = self.assistant.query_ollama("Open task manager")
        self.assertIn("Certainly, sir", reply)
        self.assertIn("Task manager opened", reply)
        mock_popen.assert_called_with("taskmgr.exe", shell=True)

    def test_empty_prompt_handling(self):
        reply = self.assistant.query_ollama("   ")
        self.assertEqual(reply, "Awaiting your command, sir.")


class TestAudioPipelineAndEdgeCases(unittest.TestCase):
    """Test audio listening loop edge cases: silence, microphone disconnection, and input filtering."""

    def setUp(self):
        self.assistant = VoiceAssistant(model_name="jarvis", voice="bm_daniel")

    def test_process_input_empty_and_whitespace(self):
        # Empty or whitespace inputs should be ignored gracefully
        self.assertTrue(self.assistant.process_input(None))
        self.assertTrue(self.assistant.process_input(""))
        self.assertTrue(self.assistant.process_input("   \t  "))

    @patch.object(VoiceAssistant, "speak")
    def test_process_input_shutdown(self, mock_speak):
        should_continue = self.assistant.process_input("goodbye")
        self.assertFalse(should_continue)
        mock_speak.assert_called_with("Shutting down. Have a wonderful day, sir.")

    @patch("sounddevice.InputStream")
    def test_listen_silent_room_timeout(self, mock_input_stream):
        # Mock stream reading silence (all zeros)
        mock_stream_instance = MagicMock()
        mock_stream_instance.read.return_value = (np.zeros((1024, 1), dtype=np.float32), False)
        mock_input_stream.return_value.__enter__.return_value = mock_stream_instance

        # max_silent_time = 0.05 seconds to quickly verify silent room timeout
        result = self.assistant.listen(max_silent_time=0.05)
        self.assertIsNone(result)

    @patch("sounddevice.InputStream", side_effect=OSError("Audio device disconnected"))
    @patch("time.sleep")
    def test_listen_microphone_disconnection_resilience(self, mock_sleep, mock_input_stream):
        result = self.assistant.listen()
        self.assertIsNone(result)
        mock_sleep.assert_called_with(1.0)


if __name__ == "__main__":
    unittest.main()
