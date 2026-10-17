"""Jarvis: Local AI Voice Assistant with Kokoro TTS, Whisper STT, and Spotify control."""

import argparse
import io
import json
import os
import re
import sys
import threading
import time
from typing import Optional, List, Tuple

try:
    import overlay
except ImportError:
    from src import overlay

from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro
import numpy as np
import requests
import scipy.io.wavfile as wav
import sounddevice as sd
import soundfile as sf

try:
    import ollama
except ImportError:
    ollama = None

from openwakeword.model import Model

# Initialize Faster-Whisper model on CPU with int8 quantization
stt_model = WhisperModel("small.en", device="cpu", compute_type="int8")


from tools.system_ctrl import (
    handle_system_command,
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


def chunk_text(text: str, max_chunk_chars: int = 180) -> List[str]:
    """Split text into spoken sentence chunks on punctuation delimiters without audio buffer clipping."""
    cleaned = text.strip()
    if not cleaned:
        return []

    # Split text on sentence and clause boundaries: periods, exclamation marks, question marks, semicolons, newlines
    raw_sentences = re.split(r'(?<=[.!?;\n])\s+', cleaned)
    chunks: List[str] = []
    current = ""

    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        if len(current) + len(s) + 1 <= max_chunk_chars:
            current = f"{current} {s}".strip() if current else s
        else:
            if current:
                chunks.append(current)
            # If an individual segment exceeds max_chunk_chars, split on commas or spaces
            if len(s) > max_chunk_chars:
                comma_parts = re.split(r'(?<=[,])\s+', s)
                sub_current = ""
                for p in comma_parts:
                    if len(sub_current) + len(p) + 1 <= max_chunk_chars:
                        sub_current = f"{sub_current} {p}".strip() if sub_current else p
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = p
                if sub_current:
                    chunks.append(sub_current)
                current = ""
            else:
                current = s

    if current:
        chunks.append(current)

    return chunks


def synthesize_speech(text: str, voice: str = CHOSEN_VOICE, speed: float = 1.1) -> Tuple[Optional[np.ndarray], int]:
    """Synthesize speech audio array using Kokoro TTS with sentence chunking to prevent buffer clipping."""
    cleaned = text.strip()
    if not cleaned:
        return None, 24000

    chunks = chunk_text(cleaned)
    if not chunks:
        return None, 24000

    audio_segments = []
    sample_rate = 24000

    for chunk in chunks:
        try:
            samples, sr = kokoro.create(chunk, voice=voice, speed=speed, lang="en-us")
            if samples is not None and len(samples) > 0:
                audio_segments.append(samples)
                sample_rate = sr
                # Subtle 50ms pause between sentence chunks for natural phrasing
                pause = np.zeros(int(sample_rate * 0.05), dtype=np.float32)
                audio_segments.append(pause)
        except Exception as err:
            print(f"[Kokoro Chunk Error on '{chunk}']: {err}")

    if not audio_segments:
        return None, sample_rate

    combined = np.concatenate(audio_segments, axis=0)
    return combined, sample_rate


_playback_end_time = 0.0


def is_audio_playing() -> bool:
    """Check if sounddevice audio playback is currently active."""
    global _playback_end_time
    try:
        stream = sd.get_stream()
        if stream is not None:
            active = getattr(stream, "active", False)
            if active is True:
                return True
            if hasattr(active, "_mock_return_value") or hasattr(active, "_mock_wraps"):
                return bool(active)
    except Exception:
        pass
    return time.time() < _playback_end_time


def speak(text: str, voice: str = CHOSEN_VOICE, speed: float = 1.1):
    """Generate and play audio non-blockingly using Kokoro TTS and sounddevice."""
    global _playback_end_time
    print(f"\n[Jarvis]: {text}\n")
    if not text or not text.strip():
        return
    try:
        combined, sample_rate = synthesize_speech(text, voice=voice, speed=speed)
        if combined is not None and len(combined) > 0:
            duration = len(combined) / sample_rate
            _playback_end_time = time.time() + duration
            overlay.JARVIS_STATE = "speaking"
            sd.play(combined, sample_rate)

            def _reset_speaking(d):
                time.sleep(d)
                if time.time() >= _playback_end_time:
                    overlay.JARVIS_STATE = "idle"

            threading.Thread(target=_reset_speaking, args=(duration,), daemon=True).start()
    except Exception as e:
        print(f"[Kokoro TTS Error]: {e}")
        overlay.JARVIS_STATE = "idle"


def listen(
    threshold: int = 500,
    silence_duration: float = 0.7,
    timeout: Optional[float] = None,
    max_silent_time: float = 8.0,
    chunk_size: int = 1024,
    samplerate: int = 16000,
    **kwargs,
) -> Optional[str]:
    """Record microphone audio via sounddevice, detect speech, stop after 0.7s silence, and transcribe via Whisper."""
    global _playback_end_time
    effective_timeout = timeout if timeout is not None else max_silent_time
    print("[Listening for speech...]")
    overlay.JARVIS_STATE = "listening"

    audio_chunks: List[np.ndarray] = []
    is_recording = False
    silence_samples = 0
    silence_limit_samples = int(silence_duration * samplerate)
    initial_silence_samples = 0
    max_initial_samples = int(effective_timeout * samplerate) if effective_timeout is not None else None

    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype="int16") as stream:
            while True:
                chunk, _ = stream.read(chunk_size)
                vol = np.max(np.abs(chunk))

                if not is_recording:
                    if vol > threshold:
                        is_recording = True
                        audio_chunks.append(chunk)
                        silence_samples = 0
                        if is_audio_playing():
                            print("[Interruption detected! Stopping speech playback...]")
                            try:
                                sd.stop()
                            except Exception:
                                pass
                            _playback_end_time = 0.0
                    else:
                        initial_silence_samples += len(chunk)
                        if max_initial_samples is not None and initial_silence_samples >= max_initial_samples:
                            return None
                else:
                    audio_chunks.append(chunk)
                    if vol < threshold:
                        silence_samples += len(chunk)
                        if silence_samples >= silence_limit_samples:
                            break
                    else:
                        silence_samples = 0

                time.sleep(0.01)

        if not audio_chunks:
            return None

        audio_data = np.concatenate(audio_chunks, axis=0)
        temp_file = "temp_dictation.wav"
        wav.write(temp_file, samplerate, audio_data)

        try:
            segments, _ = stt_model.transcribe(
                temp_file,
                beam_size=5,
                condition_on_previous_text=False,
            )
            text = " ".join(s.text for s in segments).strip()
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        return text if text else None

    except (sd.PortAudioError, OSError) as audio_err:
        print(f"[Microphone Error]: Audio device unavailable or disconnected: {audio_err}")
        time.sleep(1.0)
        return None
    except Exception as exc:
        print(f"[Audio Error]: {exc}")
        return None
    finally:
        overlay.JARVIS_STATE = "idle"


class VoiceAssistant:
    def __init__(self, model_name: str = "jarvis", voice: str = CHOSEN_VOICE, **kwargs):
        self.model_name = model_name
        self.voice = voice
        self.conversation_history = []
        self.messages = self.conversation_history
        self._transcriber = stt_model

    @property
    def transcriber(self):
        return self._transcriber

    def speak(self, text: str):
        """Forward to global speak function using chosen voice and 1.1x speed."""
        speak(text, voice=self.voice, speed=1.1)

    def listen(
        self,
        timeout: Optional[float] = None,
        max_silent_time: float = 8.0,
        **kwargs,
    ) -> Optional[str]:
        return listen(timeout=timeout, max_silent_time=max_silent_time, **kwargs)

    def query_ollama(self, user_prompt: str) -> str:
        """Send prompt to Ollama running the local jarvis model with safe tool calling support."""
        if not ollama:
            print("[Debug Error]: Ollama library is not installed in the environment.")
            return "I encountered an error, sir."

        clean_prompt = user_prompt.strip()
        if not clean_prompt:
            return "Awaiting your command, sir."

        self.conversation_history.append({"role": "user", "content": clean_prompt})

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
                    fn_info = tool.get("function", {})
                    fn_name = fn_info.get("name")
                    fn_args = fn_info.get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception as e:
                            print(f"[Debug Error - Tool Args]: {e}")
                            fn_args = {}

                    if fn_name == "control_spotify":
                        _, msg = control_spotify(action=fn_args.get("action", ""), query=fn_args.get("query", ""))
                        tool_replies.append(msg)
                    elif fn_name == "open_application":
                        _, msg = open_application(app_name=fn_args.get("app_name", ""))
                        tool_replies.append(msg)
                    elif fn_name == "get_system_stats":
                        stats = get_system_stats()
                        tool_replies.append(stats["summary"])
                    elif fn_name == "run_powershell_command":
                        cmd_out = run_powershell_command(command=fn_args.get("command", ""))
                        tool_replies.append(cmd_out)
                    elif fn_name == "search_web":
                        search_out = search_web(query=fn_args.get("query", ""), max_results=int(fn_args.get("max_results", 3)))
                        tool_replies.append(search_out)
                    elif fn_name == "manage_volume":
                        vol_out = manage_volume(action=fn_args.get("action", "mute"))
                        tool_replies.append(vol_out)
                    elif fn_name == "manage_brightness":
                        bright_out = manage_brightness(action=fn_args.get("action", "up"))
                        tool_replies.append(bright_out)
                    elif fn_name == "capture_screen":
                        screen_out = capture_screen()
                        tool_replies.append(screen_out)
                    elif fn_name == "list_running_processes":
                        procs_out = list_running_processes(limit=int(fn_args.get("limit", 10)))
                        tool_replies.append(procs_out)
                    else:
                        tool_replies.append(f"Function {fn_name} is not recognized.")

                tool_text = " ".join(tool_replies) if tool_replies else message.get("content", "").strip()
                # Feed tool execution result into conversation history with polite persona
                reply = f"Certainly, sir. {tool_text}" if tool_text else "Task completed as requested, sir."
            else:
                reply = message.get("content", "").strip()
                if not reply:
                    reply = "At your command, sir."

            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as exc:
            print(f"[Debug Error - Ollama Tool Chat]: {exc}")
            # Fallback to direct chat without tools
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=self.conversation_history[-8:],
                )
                reply = response.get("message", {}).get("content", "").strip()
                if not reply:
                    reply = "At your service, sir."
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                print(f"[Debug Error - Ollama Direct Chat]: {e}")
                return "I encountered an error, sir."

    def process_input(self, user_text: Optional[str]) -> bool:
        """Process transcribed or typed input. Returns False if user requested exit."""
        if not user_text:
            return True
        clean_text = user_text.strip()
        if not clean_text:
            return True

        lower_text = clean_text.lower()
        if lower_text in ["exit", "quit", "shutdown", "stop", "goodbye"]:
            self.speak("Shutting down. Have a wonderful day, sir.")
            return False

        # First evaluate local system & Spotify control commands
        handled, system_reply = handle_system_command(clean_text)
        if handled:
            self.speak(system_reply)
            return True

        # Otherwise query the Ollama model and speak out loud
        reply = self.query_ollama(clean_text)
        if reply and reply.strip():
            self.speak(reply)
        return True

    def run_voice_loop(self):
        """Continuously run the voice interaction loop with 'Hey Jarvis' wake word detection."""
        return run_jarvis(self)

    # Method alias on VoiceAssistant
    run_jarvis = run_voice_loop

    def run_cli_loop(self):
        """Interactive text CLI mode for testing without microphone."""
        self.speak("Jarvis CLI mode initialized.")
        try:
            while True:
                prompt = input("\nYou: ").strip()
                if not prompt or not prompt.strip():
                    continue
                should_continue = self.process_input(prompt)
                if not should_continue:
                    break
        except (KeyboardInterrupt, EOFError):
            self.speak("Jarvis shutting down. Goodbye.")


def run_jarvis(assistant: Optional[VoiceAssistant] = None):
    """Run the main Jarvis voice assistant infinite listening loop with local 'Hey Jarvis' wake word detection."""
    if assistant is None:
        assistant = VoiceAssistant()
        # Move messages array initialization outside and above while True loop for persistent context
        messages = []
        assistant.conversation_history = messages
    else:
        messages = assistant.conversation_history
    assistant.messages = messages

    try:
        import openwakeword.utils
        openwakeword.utils.download_models(model_names=["hey_jarvis"])
    except Exception:
        pass

    oww_model = Model(wakeword_models=["hey_jarvis"])
    assistant.speak("Jarvis is online and ready for commands.")
    print("\n[Jarvis]: Listening for 'Hey Jarvis' wake word...\n")

    chunk_size = 1280  # 80ms audio chunk at 16kHz for openwakeword
    sample_rate = 16000

    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16") as stream:
            while True:
                try:
                    audio_chunk, _ = stream.read(chunk_size)
                except (sd.PortAudioError, OSError) as mic_err:
                    print(f"[Microphone Error]: {mic_err}")
                    time.sleep(1.0)
                    continue

                if audio_chunk is None or len(audio_chunk) == 0:
                    continue

                prediction = oww_model.predict(audio_chunk.flatten())
                score = prediction.get("hey_jarvis", 0.0)

                if score >= 0.5:
                    print(f"\n[Wake Word]: 'Hey Jarvis' detected! (confidence: {score:.2f})")
                    oww_model.reset()
                    try:
                        stream.stop()
                    except Exception:
                        pass

                    # Immediately call speak("Yes, sir.")
                    assistant.speak("Yes, sir.")

                    # Immediately trigger Whisper transcription to listen for user command
                    user_text = assistant.listen()
                    if user_text and user_text.strip():
                        print(f"[User]: {user_text}")
                        clean_text = user_text.strip()
                        if clean_text.lower() in ["exit", "quit", "shutdown", "stop", "goodbye"]:
                            assistant.speak("Shutting down. Have a wonderful day, sir.")
                            break

                        handled, system_reply = handle_system_command(clean_text)
                        if handled:
                            assistant.speak(system_reply)
                        else:
                            messages.append({"role": "user", "content": clean_text})
                            try:
                                response = ollama.chat(model="jarvis", messages=messages, stream=True, keep_alive=-1)
                                current_sentence = ""
                                full_reply = ""
                                for chunk in response:
                                    try:
                                        content = chunk["message"]["content"]
                                    except Exception:
                                        content = getattr(getattr(chunk, "message", None), "content", "")
                                    if not content:
                                        continue
                                    current_sentence += content
                                    full_reply += content

                                    while True:
                                        match = re.search(r"([.?!])\s+", current_sentence)
                                        if not match:
                                            break
                                        end_pos = match.end()
                                        sentence = current_sentence[:end_pos].strip()
                                        current_sentence = current_sentence[end_pos:]
                                        if sentence:
                                            assistant.speak(sentence)

                                if current_sentence.strip():
                                    assistant.speak(current_sentence.strip())

                                if full_reply.strip():
                                    messages.append({"role": "assistant", "content": full_reply.strip()})
                            except Exception as exc:
                                print(f"[Ollama Error]: {exc}")
                                assistant.speak("I encountered an error, sir.")

                    oww_model.reset()
                    try:
                        stream.start()
                    except Exception:
                        pass
                    print("\n[Jarvis]: Resumed listening for 'Hey Jarvis'...\n")

                time.sleep(0.01)

    except KeyboardInterrupt:
        assistant.speak("Jarvis paused. Goodbye.")


def main():
    parser = argparse.ArgumentParser(description="Jarvis Local Voice Assistant (Kokoro TTS & Whisper STT)")
    parser.add_argument("--cli", action="store_true", help="Run in text CLI mode instead of microphone voice loop")
    parser.add_argument("--model", type=str, default="jarvis", help="Ollama model name (default: jarvis)")
    parser.add_argument("--voice", type=str, default=CHOSEN_VOICE, help="Kokoro voice (default: bm_daniel)")
    parser.add_argument("--whisper-size", type=str, default="large-v3-turbo", help=argparse.SUPPRESS)
    parser.add_argument("--stats", action="store_true", help="Print system statistics and exit")
    args = parser.parse_args()

    if args.stats:
        stats = get_system_stats()
        print(stats["summary"])
        return

    assistant = VoiceAssistant(model_name=args.model, voice=args.voice)

    if args.cli:
        assistant.run_cli_loop()
    else:
        threading.Thread(target=run_jarvis, args=(assistant,), daemon=True).start()
        overlay.root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        threading.Thread(target=run_jarvis, daemon=True).start()
        overlay.root.mainloop()

