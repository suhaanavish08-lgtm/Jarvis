"""Jarvis: Local AI Voice Assistant with Kokoro TTS (Orbit voice)."""

import argparse
import io
import json
import os
import sys
import tempfile
import time
import urllib.request
from typing import Optional

from kokoro_onnx import Kokoro
import numpy as np
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

from tools.system_ctrl import handle_system_command, get_system_stats, launch_app, open_application

# Configuration for Kokoro TTS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
KOKORO_MODEL_FILE = "kokoro-v1.0.onnx"
KOKORO_VOICES_BIN = "voices-v1.0.bin"
CHOSEN_VOICE = "am_michael"  # Deep, energetic male AI voice (Orbit-like)

KOKORO_MODEL_URL = f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{KOKORO_MODEL_FILE}"
KOKORO_VOICES_BIN_URL = f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{KOKORO_VOICES_BIN}"


def ensure_kokoro_models(model_dir: str = MODELS_DIR, voice_name: str = CHOSEN_VOICE) -> tuple[str, str]:
    """Ensure Kokoro ONNX model and chosen voice JSON/embeddings are present in models/."""
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, KOKORO_MODEL_FILE)
    voices_bin_path = os.path.join(model_dir, KOKORO_VOICES_BIN)
    voice_json_path = os.path.join(model_dir, f"{voice_name}.json")

    # 1. Download Kokoro-82M ONNX model if missing
    if not os.path.exists(model_path):
        print(f"[Jarvis] Downloading Kokoro-82M ONNX model ({KOKORO_MODEL_FILE})...")
        urllib.request.urlretrieve(KOKORO_MODEL_URL, model_path)
        print("[Jarvis] Kokoro-82M ONNX model downloaded.")

    # 2. Download voices binary if missing
    if not os.path.exists(voices_bin_path):
        print(f"[Jarvis] Downloading voices file ({KOKORO_VOICES_BIN})...")
        urllib.request.urlretrieve(KOKORO_VOICES_BIN_URL, voices_bin_path)
        print("[Jarvis] Voices binary downloaded.")

    # 3. Create/verify chosen voice JSON in models folder
    if not os.path.exists(voice_json_path):
        print(f"[Jarvis] Generating voice JSON for {voice_name} in models/...")
        try:
            voices_data = np.load(voices_bin_path)
            if voice_name in voices_data:
                voice_dict = {voice_name: voices_data[voice_name].tolist()}
                with open(voice_json_path, "w", encoding="utf-8") as f:
                    json.dump(voice_dict, f)
                print(f"[Jarvis] Saved {voice_name}.json to models/.")
        except Exception as exc:
            print(f"[Warning] Failed to generate {voice_name}.json: {exc}")

    return model_path, voices_bin_path


# Initialize Kokoro globally
_model_path, _voices_path = ensure_kokoro_models()
kokoro = Kokoro(model_path=_model_path, voices_path=_voices_path)


def speak(text: str, voice: str = CHOSEN_VOICE, speed: float = 1.0):
    """Print response to the terminal and speak out loud using Kokoro TTS & sounddevice."""
    print(f"\n[Jarvis]: {text}\n")
    if not text.strip():
        return
    try:
        samples, sample_rate = kokoro.create(
            text=text,
            voice=voice,
            speed=speed,
            lang="en-us"
        )
        sd.play(samples, sample_rate)
        sd.wait()
    except Exception as e:
        print(f"[Kokoro TTS Error]: {e}")


class VoiceAssistant:
    def __init__(self, model_name: str = "jarvis", whisper_size: str = "tiny.en", voice: str = CHOSEN_VOICE):
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
                device="cpu",
                compute_type="int8"
            )
        return self._whisper_model

    def speak(self, text: str):
        """Forward to global speak function using chosen voice."""
        speak(text, voice=self.voice)

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
        """Send prompt to Ollama running the local jarvis model."""
        if not ollama:
            return "Ollama library is not installed in the environment."

        self.conversation_history.append({"role": "user", "content": user_prompt})

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=self.conversation_history[-8:],
            )
            reply = response["message"]["content"].strip()
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                try:
                    response = ollama.chat(
                        model="llama3.2",
                        messages=self.conversation_history[-8:],
                    )
                    reply = response["message"]["content"].strip()
                    self.conversation_history.append({"role": "assistant", "content": reply})
                    return reply
                except Exception:
                    pass
            return f"Ollama connection error: {error_msg}. Please make sure Ollama is running."

    def process_input(self, user_text: str) -> bool:
        """Process transcribed or typed input. Returns False if user requested exit."""
        clean_text = user_text.strip().lower()

        if clean_text in ["exit", "quit", "shutdown", "stop", "goodbye"]:
            self.speak("Shutting down. Have a wonderful day, sir.")
            return False

        # First evaluate local system control commands
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
    parser = argparse.ArgumentParser(description="Jarvis Local Voice Assistant (Kokoro TTS)")
    parser.add_argument("--cli", action="store_true", help="Run in text CLI mode instead of microphone voice loop")
    parser.add_argument("--model", type=str, default="jarvis", help="Ollama model name (default: jarvis)")
    parser.add_argument("--voice", type=str, default=CHOSEN_VOICE, help="Kokoro voice (default: am_michael)")
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
        assistant.run_voice_loop()


if __name__ == "__main__":
    main()
