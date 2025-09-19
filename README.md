# RoboTest Jetson Orin Nano Super Installation Guide

## Overview
This project wires together three real-time components on the Jetson Orin Nano: WebRTC-based voice activity detection and microphone capture, Faster-Whisper speech recognition, Kokoro-ONNX text-to-speech playback, and a pygame-driven face animation loop while chatting with an Ollama-hosted LLM.

## 1. OS prerequisites (once per Jetson)
```bash
sudo apt update
sudo apt install -y git curl python3-venv python3-dev build-essential \
    libportaudio2 portaudio19-dev libasound-dev libsndfile1 \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libfreetype6-dev libjpeg-dev libpng-dev
```
- `pyaudio` (microphone I/O) depends on PortAudio/ALSA headers and libs.
- `webrtcvad` and `pygame` expect development headers to build on aarch64.
- `soundfile` needs `libsndfile1` for playback; `pygame` uses SDL2/FreeType/JPEG/PNG for rendering.

If you plan to display over HDMI while logged in via SSH, also enable an X server on the Jetson desktop (`DISPLAY=:0` later).

## 2. Clone the repository
```bash
mkdir -p ~/robot
cd ~/robot
git clone https://<your_repo_host>/RoboTest.git
cd RoboTest
```

## 3. Python environment
```bash
python3 -m venv ~/robot/.venv
source ~/robot/.venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt
```
Requirements pull Faster-Whisper, Kokoro-ONNX, PyAudio, pygame, WebRTC-VAD, etc.

First run will download the Faster-Whisper `tiny.en` model and Kokoro ONNX/voice files into `~/.cache/kokoro_onnx`.

## 4. Provide face assets
Place `face.png` and `mouth.png` (transparent PNGs sized for your display) in the repository root or adjust `FaceSettings.face_image_path` / `mouth_image_path` to point elsewhere.

## 5. Install and prepare Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
# either reboot or start the service manually after install:
sudo systemctl enable --now ollama
ollama run gemma3:270m   # downloads/warm-starts the model
```
The app expects to reach `http://localhost:11434/api/chat` with the `gemma3:270m` model in streaming mode.

Keep the Ollama service running in the background (`ollama serve` if you are not using systemd).

## 6. Hardware checks
1. Plug in a USB microphone and speakers/headphones.
2. Verify the devices:
   ```bash
   arecord -l   # list capture devices
   aplay -l     # list playback devices
   ```
3. Adjust ALSA mixer levels (`alsamixer`) so the WebRTC VAD sees audio above its thresholds.

If you need to target a non-default microphone, set `device_index` when creating `VADListener` (edit `main.py`).

## 7. Running the application
```bash
# still inside the venv and repo root
export DISPLAY=:0        # required only when launching over SSH
python main.py
```
The face renderer starts in its own thread, then the VAD loop blocks waiting for speech. Whisper automatically falls back to CPU if CUDA is unavailable; if ctranslate2 detects a CUDA device on the Jetson, it uses it for STT acceleration.

## 8. Runtime expectations & troubleshooting
- First launch may take a few minutes while models download (`faster-whisper`, Kokoro assets, and the Ollama LLM).
- If `pyaudio` reports missing devices, confirm PulseAudio/ALSA sees your hardware, or run the script as the desktop user instead of root to access sound.
- To tweak face orientation or screen resolution, adjust `FaceSettings` in `main.py` (window size, rotation, offsets).
- To switch voices or playback rate, pass different parameters when constructing `KokoroTTS`. Available voices can be listed via `KokoroTTS().available_voices()`.

No additional steps are required beyond the apt packages above unless your JetPack installation lacks CUDA/cuDNN updates; the script already tolerates CPU-only inference.
