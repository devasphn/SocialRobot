"""Entrypoint for the robot face and dialogue loop."""

from __future__ import annotations

import threading
from typing import Optional

from audio.stt import FasterWhisperSTT
from audio.tts import EspeakTTS
from audio.vad import VADConfig, VADListener
from face_animation.face import FaceAnimator, FaceSettings
from llm.ollama import OllamaClient


def _detect_whisper_device() -> str:
    try:
        import ctranslate2  # type: ignore

        if ctranslate2.get_cuda_device_count() > 0:  # type: ignore[attr-defined]
            return "cuda"
    except Exception:
        pass
    return "cpu"


def main() -> None:
    face_settings = FaceSettings(window_size=(1920, 1080), rotation_degrees=-90)
    face_animator = FaceAnimator(settings=face_settings)
    face_thread = threading.Thread(target=face_animator.run, daemon=True)
    face_thread.start()

    vad_config = VADConfig(sample_rate=16000, frame_duration_ms=30, padding_duration_ms=360, aggressiveness=2)

    stt_device = _detect_whisper_device()
    stt_model = FasterWhisperSTT(model_size_or_path="tiny.en", device=stt_device, compute_type="int8")

    ollama_client = OllamaClient(
        url="http://localhost:11434/api/chat",
        model="gemma3:270m",
        stream=True,
        system_prompt="You are a cheerful robotic companion speaking concisely.",
    )

    tts_model = EspeakTTS(voice="en-us", rate=185, pitch=55)

    vad_listener: Optional[VADListener] = None
    last_bot_response: str = ""

    def on_speech_detected(raw_bytes: bytes) -> None:
        nonlocal vad_listener, last_bot_response
        if vad_listener is None:
            return

        vad_listener.disable_vad()

        try:
            recognized_text = stt_model.run_stt(raw_bytes, sample_rate=vad_listener.sample_rate)
        except Exception as exc:  # pragma: no cover - defensive logging only
            print("STT error:", exc)
            recognized_text = ""

        print("-> User said:", recognized_text)

        if not recognized_text.strip():
            face_animator.update_amplitude(0.0)
            vad_listener.enable_vad()
            return

        normalized_user = recognized_text.strip().lower()
        normalized_bot = last_bot_response.strip().lower()
        if normalized_user and normalized_bot:
            if (
                normalized_user == normalized_bot
                or normalized_user in normalized_bot
                or normalized_bot in normalized_user
            ):
                print("-> Ignoring self-echo from recent response.")
                face_animator.update_amplitude(0.0)
                vad_listener.enable_vad()
                return

        llm_response = ollama_client.query(recognized_text)
        if not llm_response.strip():
            face_animator.update_amplitude(0.0)
            vad_listener.enable_vad()
            return

        try:
            audio_data = tts_model.synthesize(llm_response)
        except Exception as exc:  # pragma: no cover - defensive logging only
            print("TTS error:", exc)
            face_animator.update_amplitude(0.0)
            vad_listener.enable_vad()
            return

        last_bot_response = llm_response

        def amplitude_callback(level: float) -> None:
            face_animator.update_amplitude(level)

        tts_model.play_audio_with_amplitude(audio_data, amplitude_callback)
        face_animator.update_amplitude(0.0)
        vad_listener.enable_vad()

    vad_listener = VADListener(config=vad_config, device_index=None, on_speech_callback=on_speech_detected)

    print("-> Starting the VAD listener...")
    try:
        vad_listener.start()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        vad_listener.stop()
        face_animator.stop()


if __name__ == "__main__":
    main()
