"""Text-to-speech utilities built on top of eSpeak NG."""

from __future__ import annotations

import io
import subprocess
from typing import Callable, List, Optional

import numpy as np
import pyaudio
import soundfile as sf


class EspeakTTS:
    """Generate audio using the `espeak`/`espeak-ng` command line synthesiser."""

    def __init__(
        self,
        voice: str = "en-us",
        rate: int = 180,
        pitch: int = 50,
        volume: int = 100,
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.sample_rate = 22050  # Will be updated after first synthesis
        self._binary = self._detect_binary()
        print(f"-> Using {self._binary} for speech synthesis.")

    @staticmethod
    def _detect_binary() -> str:
        for candidate in ("espeak-ng", "espeak"):
            try:
                subprocess.run([candidate, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return candidate
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        raise RuntimeError("Neither 'espeak-ng' nor 'espeak' is installed.")

    def synthesize(self, text: str) -> np.ndarray:
        if not text:
            return np.zeros(0, dtype=np.float32)

        cmd = [
            self._binary,
            "-v",
            self.voice,
            "-s",
            str(self.rate),
            "-p",
            str(self.pitch),
            "-a",
            str(self.volume),
            "--stdout",
            text,
        ]

        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_bytes = result.stdout
        if not audio_bytes:
            return np.zeros(0, dtype=np.float32)

        audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if audio.ndim > 1:
            audio = audio[:, 0]
        self.sample_rate = sr
        return audio

    def _chunk_audio(self, audio_data: np.ndarray, chunk_size: int) -> List[np.ndarray]:
        return [audio_data[i : i + chunk_size] for i in range(0, len(audio_data), chunk_size)]

    def play_audio_with_amplitude(
        self,
        audio_data: np.ndarray,
        amplitude_callback: Optional[Callable[[float], None]] = None,
        chunk_duration: float = 0.02,
    ) -> None:
        if audio_data is None or len(audio_data) == 0:
            if amplitude_callback:
                amplitude_callback(0.0)
            return

        audio_float = audio_data.astype(np.float32)
        chunk_size = max(1, int(self.sample_rate * chunk_duration))
        chunks = self._chunk_audio(audio_float, chunk_size)
        if not chunks:
            return

        rms_values = [float(np.sqrt(np.mean(np.square(chunk)) + 1e-8)) for chunk in chunks]
        max_rms = max(rms_values) or 1.0
        normalized_levels = [min(rms / max_rms, 1.0) for rms in rms_values]

        audio_int16 = np.clip(audio_float * 32767.0, -32768, 32767).astype(np.int16)

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True,
        )

        cursor = 0
        for chunk, level in zip(chunks, normalized_levels):
            frames = audio_int16[cursor : cursor + len(chunk)]
            stream.write(frames.tobytes())
            cursor += len(chunk)
            if amplitude_callback:
                amplitude_callback(level)

        if amplitude_callback:
            amplitude_callback(0.0)

        stream.stop_stream()
        stream.close()
        pa.terminate()


__all__ = ["EspeakTTS"]
