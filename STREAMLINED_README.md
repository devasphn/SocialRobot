# Streamlined Speech-to-Speech AI Pipeline

> **This is a pure STT-LLM-TTS implementation focused solely on speech-to-speech conversation without visual components, face animation, or Arduino hardware.**

## Overview

This streamlined fork removes all non-essential components from the original SocialRobot project to create a pure speech-to-speech AI pipeline. The implementation includes:

- **Speech-to-Text (STT)**: Faster-Whisper for audio transcription
- **Large Language Model (LLM)**: Ollama integration for conversational AI
- **Text-to-Speech (TTS)**: Kokoro-ONNX for natural speech synthesis
- **Voice Activity Detection (VAD)**: WebRTC-based speech detection

## What was Removed

- Face animation system (`face_animation/` directory)
- Arduino control setup (`Arduino_Setup/` directory)  
- Visual assets and images (`images/` directory)
- GUI components and visual dependencies
- 3D printing files and hardware requirements
- All hardware-specific dependencies

## Requirements

### System Dependencies

```bash
sudo apt update
sudo apt install -y git curl python3-venv python3-dev build-essential \\
    libportaudio2 portaudio19-dev libasound-dev
```

### Python Dependencies

Install from the streamlined requirements file:

```bash
python3 -m venv ~/.venv/speech-pipeline
source ~/.venv/speech-pipeline/bin/activate
pip install -r streamlined_requirements.txt
```

**Core Dependencies:**
- `faster-whisper==1.0.3` - Speech-to-text processing
- `kokoro-onnx==0.4.9` - Text-to-speech synthesis
- `PyAudio==0.2.14` - Audio input/output
- `webrtcvad==2.0.10` - Voice activity detection
- `requests==2.32.3` - HTTP requests for LLM API
- `numpy==2.2.1` - Numerical computations

## Setup

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run gemma3:270m  # Downloads the gemma3 270m model
```

### 2. Configure Audio

1. Connect a USB microphone and speakers/headphones
2. Set default audio devices via system settings
3. For headless operation, configure PulseAudio:

```bash
pactl list short sinks       # identify output devices
pactl set-default-sink <sink_name>

pactl list short sources     # identify microphone input
pactl set-default-source <source_name>
```

### 3. Clone and Run

```bash
git clone https://github.com/devasphn/SocialRobot.git
cd SocialRobot
source ~/.venv/speech-pipeline/bin/activate
python streamlined_main.py
```

## Usage

1. Ensure Ollama is running (`ollama serve` if not using systemd)
2. Run the streamlined pipeline: `python streamlined_main.py`
3. Speak into your microphone to begin conversation
4. The AI will respond with synthesized speech
5. Press `Ctrl+C` to exit

## Technical Details

### Voice Activity Detection
- Uses WebRTC VAD with configurable aggressiveness
- Automatically handles audio streaming and buffering
- Includes echo cancellation to prevent feedback loops

### Speech-to-Text
- Faster-Whisper with "tiny.en" model for English transcription
- Automatic CUDA/CPU device detection
- Configurable precision (int8 by default)

### Language Model
- Ollama integration with streaming responses
- Default model: `gemma3:270m` (lightweight but capable)
- Configurable system prompt and parameters

### Text-to-Speech
- Kokoro-ONNX for high-quality speech synthesis
- Multiple voice options available
- Configurable speed and audio parameters

## File Structure (Streamlined)

```
SocialRobot/
├── streamlined_main.py          # Main application entry point
├── streamlined_requirements.txt  # Minimal dependencies
├── audio/                       # Audio processing modules
│   ├── stt.py                  # Speech-to-text implementation
│   ├── tts.py                  # Text-to-speech implementation
│   └── vad.py                  # Voice activity detection
├── llm/                        # LLM integration
│   └── ollama.py               # Ollama client
└── STREAMLINED_README.md        # This file
```

## Performance Notes

- First run downloads models (may take several minutes)
- CUDA acceleration used automatically if available
- CPU fallback for systems without GPU support
- Minimal memory footprint compared to full robot implementation

## Troubleshooting

### Audio Issues
- Verify microphone permissions and access
- Check PulseAudio/ALSA device availability
- Ensure correct default audio devices are set

### Model Issues
- Confirm Ollama is running: `ollama serve`
- Verify model availability: `ollama list`
- Check API connectivity: `curl http://localhost:11434/api/tags`

### Performance Issues
- Monitor CPU/memory usage during operation
- Consider using smaller models for resource-constrained systems
- Adjust VAD sensitivity if needed

## License

This streamlined version maintains the same license as the original SocialRobot project.
