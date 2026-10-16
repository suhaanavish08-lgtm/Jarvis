"""Jarvis: Local AI Voice Assistant."""

import argparse
import io
import os
import sys
import tempfile
import time
from typing import Optional

import numpy as np
import pyttsx3
import scipy.io.wavfile as wavfile
import sounddevice as sd

try:
    import ollama
except ImportError:
    ollama = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from tools.system_ctrl import handle_system_command, get_system_stats, launch_app


class VoiceAssistant:
    def __init__(self, model_name: str = "jarvis", whisper_size: str = "tiny.en"):
        self.model_name = model_name
        self.whisper_size = whisper_size
        self.conversation_history = []
        
        # Initialize TTS
        try:
            self.tts_engine = pyttsx3.init()
            # Set speaking rate and volume
            self.tts_engine.setProperty("rate", 180)
            self.tts_engine.setProperty("volume", 0.9)
            voices = self.tts_engine.getProperty("voices")
            if voices:
                self.tts_engine.setProperty("voice", voices[0].id)
        except Exception as e:
            print(f"[Warning] Failed to initialize pyttsx3: {e}")
            self.tts_engine = None

        # Faster-whisper model lazy loading
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
        """Speak out text and print to console."""
        print(f"\n[Jarvis]: {text}\n")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"[TTS Error]: {e}")

    def listen(self, duration: int = 5, sample_rate: int = 16000) -> Optional[str]:
        """Record audio from default microphone and transcribe via faster-whisper."""
        try:
            print(f"[Listening for {duration} seconds... speak now]")
            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            print("[Transcribing audio...]")

            # Convert to int16 for wav file format
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
            # Fallback if jarvis model not created or Ollama server down
            error_msg = str(e)
            if "not found" in error_msg.lower():
                try:
                    # Attempt fallback to llama3.2 if available
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

        # Otherwise query the Ollama model
        reply = self.query_ollama(user_text)
        self.speak(reply)
        return True

    def run_voice_loop(self, duration: int = 5):
        """Continuously run the voice interaction loop."""
        self.speak("Jarvis is online and ready for commands.")
        try:
            while True:
                user_text = self.listen(duration=duration)
                if user_text:
                    print(f"[User]: {user_text}")
                    should_continue = self.process_input(user_text)
                    if not should_continue:
                        break
                else:
                    time.sleep(0.5)
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
    parser = argparse.ArgumentParser(description="Jarvis Local Voice Assistant")
    parser.add_argument("--cli", action="store_true", help="Run in text CLI mode instead of microphone voice loop")
    parser.add_argument("--model", type=str, default="jarvis", help="Ollama model name (default: jarvis)")
    parser.add_argument("--listen-duration", type=int, default=5, help="Audio record duration in seconds")
    parser.add_argument("--stats", action="store_true", help="Print system statistics and exit")
    args = parser.parse_args()

    if args.stats:
        stats = get_system_stats()
        print(stats["summary"])
        return

    assistant = VoiceAssistant(model_name=args.model)

    if args.cli:
        assistant.run_cli_loop()
    else:
        assistant.run_voice_loop(duration=args.listen_duration)


if __name__ == "__main__":
    main()
