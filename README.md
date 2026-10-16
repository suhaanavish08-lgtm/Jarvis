# Jarvis: Local AI Desktop Voice Assistant

An ultra-responsive local voice assistant running offline with local LLM reasoning, speech-to-text, neural text-to-speech, and desktop control capabilities.

## Architecture

- **LLM Reasoning**: [Ollama](https://ollama.com/) with customized `jarvis` model (based on `llama3.2` with temperature 0.2).
- **Speech-to-Text (STT)**: `faster-whisper` (`large-v3-turbo`, `compute_type="int8"`, `device="auto"`) and `sounddevice` for accurate local audio transcription.
- **Neural Text-to-Speech (TTS)**: `kokoro-onnx` with Kokoro-82M model and `am_michael` / `am_onyx` voice embeddings (Orbit-like deep, energetic male AI voice) played via `sounddevice`.
- **System Control**: `src/tools/system_ctrl.py` monitoring CPU, RAM, disk, battery, and launching applications (Antigravity IDE, Spotify, Notepad, Calculator, etc.).

## Directory Structure

```text
Jarvis/
├── .gitignore
├── Modelfile
├── requirements.txt
├── README.md
├── models/             # Kokoro-82M ONNX model, voice JSONs & weights
├── memory/             # Local memory / conversation logs
└── src/
    ├── __init__.py
    ├── main.py         # Voice loop & CLI orchestrator with Kokoro TTS
    └── tools/
        ├── __init__.py
        └── system_ctrl.py  # System stats & app launcher (Spotify, etc.)
```

## Quick Start

### 1. Setup Virtual Environment

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Install dependencies:
pip install -r requirements.txt
```

### 2. Create the Ollama Model

Ensure [Ollama](https://ollama.com/) is installed and running:
```bash
ollama create jarvis -f Modelfile
```

### 3. Run Jarvis

Voice loop mode:
```bash
python src/main.py
```

CLI test mode (text input):
```bash
python src/main.py --cli
```

Check system stats directly:
```bash
python src/main.py --stats
```

## Built-in Commands & Tools

- **System Diagnostics**: "How is the system?", "CPU usage", "System status"
- **App Launching**:
  - "Open Antigravity" / "Launch Antigravity"
  - "Open Spotify"
  - "Open Notepad"
  - "Launch Calculator"
- **General Queries**: Handled via the local `jarvis` Llama 3.2 model with concise voice-oriented responses spoken through Kokoro neural TTS.
