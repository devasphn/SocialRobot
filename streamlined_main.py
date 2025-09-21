"""Streamlined Speech-to-Speech AI Pipeline.

This is a pure STT-LLM-TTS implementation without face animation,
Arduino components, or visual elements.
"""
from __future__ import annotations
from typing import Optional
from audio.stt import FasterWhisperSTT
from audio.tts import KokoroTTS
from audio.vad import VADConfig, VADListener
from llm.ollama import OllamaClient


def _detect_whisper_device() -> str:
    """Detects the best available device for ctranslate2 (CUDA or CPU)."""
    try:
        import ctranslate2  # type: ignore
        if ctranslate2.get_cuda_device_count() > 0:  # type: ignore[attr-defined]
            return "cuda"
    except Exception:
        pass
    return "cpu"


def main() -> None:
    """Initializes all components and starts the main interaction loop."""
    print("Initializing Speech-to-Speech AI Pipeline...")
    
    # Voice Activity Detection configuration
    vad_config = VADConfig(
        sample_rate=16000,
        frame_duration_ms=30,
        padding_duration_ms=360,
        aggressiveness=2
    )
    
    # Speech-to-Text setup
    stt_device = _detect_whisper_device()
    print(f"Using device for STT: {stt_device}")
    stt_model = FasterWhisperSTT(
        model_size_or_path="tiny.en",
        device=stt_device,
        compute_type="int8"
    )
    
    # LLM setup
    ollama_client = OllamaClient(
        url="http://localhost:11434/api/chat",
        model="gemma3:270m",
        stream=True,
        system_prompt="You are a helpful AI assistant speaking concisely.",
    )
    
    # Text-to-Speech setup
    tts_model = KokoroTTS(voice="af_bella", speed=1.0)
    
    vad_listener: Optional[VADListener] = None
    last_bot_response: str = ""
    
    def on_speech_detected(raw_bytes: bytes) -> None:
        """Callback function triggered when VAD detects speech."""
        nonlocal vad_listener, last_bot_response
        
        if vad_listener is None:
            return
            
        vad_listener.disable_vad()
        
        try:
            recognized_text = stt_model.run_stt(
                raw_bytes, 
                sample_rate=vad_listener.sample_rate
            )
        except Exception as exc:
            print("STT error:", exc)
            recognized_text = ""
            
        print(f"User said: {recognized_text}")
        
        if not recognized_text.strip():
            vad_listener.enable_vad()
            return
            
        # Simple echo cancellation
        normalized_user = recognized_text.strip().lower()
        normalized_bot = last_bot_response.strip().lower()
        
        if normalized_user and normalized_bot:
            if (
                normalized_user == normalized_bot
                or normalized_user in normalized_bot
                or normalized_bot in normalized_user
            ):
                print("Ignoring self-echo from recent response.")
                vad_listener.enable_vad()
                return
                
        # Get LLM response
        llm_response = ollama_client.query(recognized_text)
        print(f"AI response: {llm_response}")
        
        if not llm_response.strip():
            vad_listener.enable_vad()
            return
            
        try:
            # Synthesize speech
            audio_data = tts_model.synthesize(llm_response)
            
            # Play audio (simplified without amplitude callback)
            tts_model.play_audio(audio_data)
            
        except Exception as exc:
            print("TTS error:", exc)
            
        last_bot_response = llm_response
        vad_listener.enable_vad()
    
    # Start VAD listener
    vad_listener = VADListener(
        config=vad_config,
        device_index=None,
        on_speech_callback=on_speech_detected
    )
    
    print("Starting Speech-to-Speech Pipeline...")
    print("Say something to begin conversation (Ctrl+C to exit)")
    
    try:
        vad_listener.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if vad_listener:
            vad_listener.stop()
        print("Pipeline stopped.")


if __name__ == "__main__":
    main()
