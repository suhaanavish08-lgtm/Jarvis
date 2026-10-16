# Jarvis: Local AI Desktop Voice Assistant

An ultra-responsive local voice assistant running offline with local LLM reasoning, speech-to-text, text-to-speech, and desktop control capabilities.

## Architecture

- **LLM Reasoning**: [Ollama](https://ollama.com/) with customized `jarvis` model (based on `llama3.2` with temperature 0.2).
- **Speech-to-Text (STT)**: `faster-whisper` and `sounddevice` for fast local audio transcription.
- **Text-to-Speech (TTS)**: `pyttsx3` for low-latency offline voice output.
- **System Control**: `src/tools/system_ctrl.py` monitoring CPU, RAM, disk, battery, and launching applications (Antigravity IDE, Notepad, Calculator, etc.).

## Directory Structure

```text
Jarvis/
├── .gitignore
├── Modelfile
├── requirements.txt
├── README.md
├── models/             # Local model caches
├── memory/             # Local memory / conversation logs
└── src/
    ├── __init__.py
    ├── main.py         # Voice loop & CLI orchestrator
    └── tools/
        ├── __init__.py
        └── system_ctrl.py  # System stats & app launcher
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
python -m src.main
```

CLI test mode (text input):
```bash
python -m src.main --cli
```

Check system stats directly:
```bash
python -m src.main --stats
```

## Built-in Commands & Tools

- **System Diagnostics**: "How is the system?", "CPU usage", "System status"
- **App Launching**:
  - "Open Antigravity" / "Launch Antigravity"
  - "Open Notepad"
  - "Launch Calculator"
- **General Queries**: Handled via the local `jarvis` Llama 3.2 model with concise voice-oriented responses.
