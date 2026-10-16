"""Jarvis: Local AI Voice Assistant with Kokoro TTS, Whisper large-v3-turbo, and Spotify control."""

import argparse
import io
import json
import os
import sys
import tempfile
import time
from typing import Optional

from kokoro_onnx import Kokoro
import numpy as np
import requests
import scipy.io.wavfile as wavfile
import sounddevice as sd
import soundfile as sf

try:
    import ollama
except ImportError:
    ollama = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from tools.system_ctrl import (
    handle_system_command,
    get_system_stats,
    launch_app,
    open_application,
    control_spotify,
    TOOL_SCHEMAS,
)

# Configuration for Kokoro TTS (v1.0 model & voices-v1.0.bin)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
KOKORO_MODEL_FILE = "kokoro-v1.0.onnx"
KOKORO_VOICES_FILE = "voices-v1.0.bin"
CHOSEN_VOICE = "bm_daniel"

KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def ensure_kokoro_models(model_dir: str = MODELS_DIR) -> tuple[str, str]:
    """Ensure Kokoro v1.0 ONNX model and voices-v1.0.bin exist in models/ using requests."""
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, KOKORO_MODEL_FILE)
    voices_path = os.path.join(model_dir, KOKORO_VOICES_FILE)

    if not os.path.exists(model_path):
        print(f"[Jarvis] Downloading {KOKORO_MODEL_FILE} from GitHub releases...")
        response = requests.get(KOKORO_MODEL_URL, stream=True)
        response.raise_for_status()
        with open(model_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1048576):
                if chunk:
                    f.write(chunk)
        print(f"[Jarvis] {KOKORO_MODEL_FILE} downloaded successfully.")

    if not os.path.exists(voices_path):
        print(f"[Jarvis] Downloading {KOKORO_VOICES_FILE} from GitHub releases...")
        response = requests.get(KOKORO_VOICES_URL, stream=True)
        response.raise_for_status()
        with open(voices_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        print(f"[Jarvis] {KOKORO_VOICES_FILE} downloaded successfully.")

    return model_path, voices_path


# Initialize Kokoro globally
_model_path, _voices_path = ensure_kokoro_models()
kokoro = Kokoro(model_path=_model_path, voices_path=_voices_path)


def speak(text: str, voice: str = "bm_daniel", speed: float = 1.1):
    """Generate audio using Kokoro TTS with voice='bm_daniel' and speed=1.1, playing via sounddevice."""
    print(f"\n[Jarvis]: {text}\n")
    if not text.strip():
        return
    try:
        samples, sample_rate = kokoro.create(
            text,
            voice=voice,
            speed=speed,
            lang="en-us"
        )
        sd.play(samples, sample_rate)
        sd.wait()
    except Exception as e:
        print(f"[Kokoro TTS Error]: {e}")


class VoiceAssistant:
    def __init__(self, model_name: str = "jarvis", whisper_size: str = "large-v3-turbo", voice: str = "bm_daniel"):
        self.model_name = model_name
        self.whisper_size = whisper_size
        self.voice = voice
        self.conversation_history = []
        self._whisper_model = None

    @property
    def whisper_model(self):
        if self._whisper_model is None:
            if WhisperModel is None:
                raise RuntimeError("faster-whisper is not installed.")
            print(f"[Jarvis] Loading Whisper model ({self.whisper_size})...")
            self._whisper_model = WhisperModel(
                self.whisper_size,
                device="auto",
                compute_type="int8"
            )
        return self._whisper_model

    def speak(self, text: str):
        """Forward to global speak function using chosen voice and 1.1x speed."""
        speak(text, voice=self.voice, speed=1.1)

    def listen(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        speech_threshold: float = 0.03,
        silence_threshold: float = 0.02,
        silence_timeout: float = 1.5,
    ) -> Optional[str]:
        """Record audio dynamically using InputStream and silence detection, then transcribe."""
        try:
            print("[Listening for speech...]")
            frames = []
            pre_buffer = []
            pre_buffer_max_chunks = int(0.3 * sample_rate / chunk_size)  # Keep ~300ms pre-speech
            is_speaking = False
            silence_start_time = None

            with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
                while True:
                    chunk, _ = stream.read(chunk_size)
                    volume = float(np.max(np.abs(chunk)))

                    if not is_speaking:
                        pre_buffer.append(chunk)
                        if len(pre_buffer) > pre_buffer_max_chunks:
                            pre_buffer.pop(0)

                        if volume >= speech_threshold:
                            is_speaking = True
                            frames.extend(pre_buffer)
                            frames.append(chunk)
                            silence_start_time = None
                            print("[Speech detected, recording...]")
                    else:
                        frames.append(chunk)
                        if volume < silence_threshold:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time >= silence_timeout:
                                break
                        else:
                            silence_start_time = None

            if not frames:
                return None

            print("[Transcribing audio...]")
            audio_data = np.concatenate(frames, axis=0)
            audio_int16 = (audio_data * 32767).astype(np.int16)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_path = tmp_wav.name
                wavfile.write(tmp_path, sample_rate, audio_int16)

            try:
                segments, _ = self.whisper_model.transcribe(
                    tmp_path,
                    beam_size=1,
                    vad_filter=True
                )
                text = " ".join([segment.text for segment in segments]).strip()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            return text if text else None

        except Exception as exc:
            print(f"[Audio Error]: {exc}")
            return None

    def query_ollama(self, user_prompt: str) -> str:
        """Send prompt to Ollama running the local jarvis model with tool support."""
        if not ollama:
            return "Ollama library is not installed in the environment."

        self.conversation_history.append({"role": "user", "content": user_prompt})

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=self.conversation_history[-8:],
                tools=TOOL_SCHEMAS,
            )
            message = response.get("message", {})
            tool_calls = message.get("tool_calls")
            if tool_calls:
                tool_replies = []
                for tool in tool_calls:
                    fn_name = tool.get("function", {}).get("name")
                    fn_args = tool.get("function", {}).get("arguments", {})
                    if fn_name == "control_spotify":
                        _, msg = control_spotify(action=fn_args.get("action", ""), query=fn_args.get("query", ""))
                        tool_replies.append(msg)
                    elif fn_name == "open_application":
                        _, msg = open_application(app_name=fn_args.get("app_name", ""))
                        tool_replies.append(msg)
                    elif fn_name == "get_system_stats":
                        stats = get_system_stats()
                        tool_replies.append(stats["summary"])

                reply = " ".join(tool_replies) if tool_replies else message.get("content", "").strip()
            else:
                reply = message.get("content", "").strip()

            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception:
            # Fallback to direct chat without tools
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=self.conversation_history[-8:],
                )
                reply = response["message"]["content"].strip()
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                return f"Ollama connection error: {e}. Please make sure Ollama is running."

    def process_input(self, user_text: str) -> bool:
        """Process transcribed or typed input. Returns False if user requested exit."""
        clean_text = user_text.strip().lower()

        if clean_text in ["exit", "quit", "shutdown", "stop", "goodbye"]:
            self.speak("Shutting down. Have a wonderful day, sir.")
            return False

        # First evaluate local system & Spotify control commands
        handled, system_reply = handle_system_command(user_text)
        if handled:
            self.speak(system_reply)
            return True

        # Otherwise query the Ollama model and speak out loud
        reply = self.query_ollama(user_text)
        self.speak(reply)
        return True

    def run_voice_loop(self):
        """Continuously run the voice interaction loop with dynamic silence detection."""
        self.speak("Jarvis is online and ready for commands.")
        try:
            while True:
                user_text = self.listen()
                if user_text:
                    print(f"[User]: {user_text}")
                    should_continue = self.process_input(user_text)
                    if not should_continue:
                        break
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            self.speak("Jarvis paused. Goodbye.")

    def run_cli_loop(self):
        """Interactive text CLI mode for testing without microphone."""
        self.speak("Jarvis CLI mode initialized.")
        try:
            while True:
                prompt = input("\nYou: ").strip()
                if not prompt:
                    continue
                should_continue = self.process_input(prompt)
                if not should_continue:
                    break
        except (KeyboardInterrupt, EOFError):
            self.speak("Jarvis shutting down. Goodbye.")


def main():
    parser = argparse.ArgumentParser(description="Jarvis Local Voice Assistant (Kokoro TTS & Whisper large-v3-turbo)")
    parser.add_argument("--cli", action="store_true", help="Run in text CLI mode instead of microphone voice loop")
    parser.add_argument("--model", type=str, default="jarvis", help="Ollama model name (default: jarvis)")
    parser.add_argument("--voice", type=str, default=CHOSEN_VOICE, help="Kokoro voice (default: bm_daniel)")
    parser.add_argument("--whisper-size", type=str, default="large-v3-turbo", help="Whisper model size (default: large-v3-turbo)")
    parser.add_argument("--stats", action="store_true", help="Print system statistics and exit")
    args = parser.parse_args()

    if args.stats:
        stats = get_system_stats()
        print(stats["summary"])
        return

    assistant = VoiceAssistant(model_name=args.model, whisper_size=args.whisper_size, voice=args.voice)

    if args.cli:
        assistant.run_cli_loop()
    else:
        assistant.run_voice_loop()


if __name__ == "__main__":
    main()
