# RoboTest Jetson Orin Nano Super Installation Guide

## Overview
This project wires together three real-time components on the Jetson Orin Nano: WebRTC-based voice activity detection and microphone capture, Faster-Whisper speech recognition, Kokoro-ONNX text-to-speech playback, and a pygame-driven face animation loop while chatting with an Ollama-hosted LLM.

## 1. OS prerequisites (once per Jetson)
```bash
sudo apt update
sudo apt install -y git curl python3-venv python3-dev build-essential \
    libportaudio2 portaudio19-dev libasound-dev \
    libsdl2-dev libsdl2-image-dev libpng-dev
```
- `pyaudio` (microphone I/O) depends on PortAudio/ALSA headers and libs.
- `webrtcvad` and `pygame` expect development headers to build on aarch64.
- `pygame` uses SDL2 and libpng for rendering; install SDL mixer/TTF and image codecs only if your project needs them.

If you plan to display over HDMI while logged in via SSH, also enable an X server on the Jetson desktop (`DISPLAY=:0` later).

## 2. Clone the repository
```bash
git clone https://github.com/OminousIndustries/RoboTest.git
cd RoboTest
```

## 3. Python environment
```bash
python3 -m venv ~/robot/.venv
source ~/robot/.venv/bin/activate
python -m pip install -r requirements.txt
```
Requirements pull Faster-Whisper, Kokoro-ONNX, PyAudio, pygame, WebRTC-VAD, etc.

First run will download the Faster-Whisper `tiny.en` model and Kokoro ONNX/voice files into `~/.cache/kokoro_onnx`.

## 4. Provide face assets
Place `face.png` and `mouth.png` (transparent PNGs sized for your display) in the repository root or adjust `FaceSettings.face_image_path` / `mouth_image_path` to point elsewhere.

## 5. Install and prepare Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run gemma3:270m   # downloads the gemma3 270m model
```
The app expects to reach `http://localhost:11434/api/chat` with the `gemma3:270m` model in streaming mode.

Keep the Ollama service running in the background (`ollama serve` if you are not using systemd).

## 6. Hardware checks
1. Plug in a USB microphone and speakers/headphones.
2. In the system settings application, set the microphone and the speaker to the default values for sound input and output.
3. If you install the Jetson in the Robot, you will have to ensure the sound output is still set to HDMI, since this will be difficult to do while installed in the robot, you can do it through ssh like this:
```bash
# List the available audio outputs
pactl list short sinks

# This command will give you a list of your available audio outputs (sinks). The output will look something like this:
0	alsa_output.platform-sound.analog-stereo	module-alsa-card.c	s16le 2ch 44100Hz	SUSPENDED
1	alsa_output.platform-3510000.hda.hdmi-stereo	module-alsa-card.c	s16le 2ch 44100Hz	SUSPENDED

# From the list, you need to find the device that corresponds to your HDMI output. Look for a name that includes "hdmi". In the example above, the HDMI output is the second one.

# You will need this full name for the next step. You can copy it directly from your terminal.
pactl set-default-sink your_hdmi_device_name

# To find the microphone source name, run the following:
pactl list short sources

# When you see the microphone name displayed, set it as the default device: 
pactl set-default-source your_input_device_name

# This wont persist after a reboot unless you edit the  PulseAudio configuration file.
```

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
- If the software update popup is blocking the projected image, run 
# If the Ubuntu update screen overlay is blocking the display, do the following:
```bash
pgrep -af update # This will locate the process for the update window
# Once the process is shown, note its PID # and then use:
kill <PID>
# Once this is done the update popup will go away and not interfere with the projected image.
```

No additional steps are required beyond the apt packages above unless your JetPack installation lacks CUDA/cuDNN updates; the script already tolerates CPU-only inference.
