"""
NVIDIA Riva Text-to-Speech Module - Converts text to speech using NVIDIA's Riva API.
Provides an alternative TTS option with high-quality neural voices.
"""

import io
import os
import tempfile
import threading
import time
from typing import Optional, Callable
import grpc
import pygame

try:
    import riva.client
    RIVA_AVAILABLE = True
except ImportError:
    RIVA_AVAILABLE = False

import sys
sys.path.append('..')
from config import config


class NvidiaTTS:
    """
    Handles text-to-speech using NVIDIA Riva API via NVCF.
    
    Features:
    - High-quality neural TTS
    - Multiple voice options
    - Interruptible playback
    """
    
    def __init__(self):
        """Initialize NVIDIA Riva TTS client."""
        if not RIVA_AVAILABLE:
            raise ImportError("nvidia-riva-client is not installed. Run: pip install nvidia-riva-client")
        
        # Initialize pygame mixer for audio playback
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except:
            if not pygame.mixer.get_init():
                 pygame.mixer.init()
        
        # NVIDIA Riva settings
        self.server = config.NVIDIA_TTS_SERVER
        self.function_id = config.NVIDIA_TTS_FUNCTION_ID
        self.api_key = config.NVIDIA_API_KEY
        self.voice = config.NVIDIA_TTS_VOICE
        self.language = config.NVIDIA_TTS_LANGUAGE
        
        # Create auth metadata for gRPC calls
        self.metadata = [
            ("function-id", self.function_id),
            ("authorization", f"Bearer {self.api_key}")
        ]
        
        # Create Riva Auth object with correct parameters for NVCF
        self.auth = riva.client.Auth(
            uri=self.server,
            use_ssl=True,
            metadata_args=self.metadata
        )
        
        # Create TTS service
        self.tts_service = riva.client.SpeechSynthesisService(self.auth)
        
        # Playback state
        self._is_playing = False
        self._should_stop = False
        self.playback_thread: Optional[threading.Thread] = None
        
        # Text tracking
        self.current_text = ""
        self.spoken_text = ""
        
        # Callbacks
        self.on_playback_start: Optional[Callable] = None
        self.on_playback_end: Optional[Callable] = None
        
        # SSML settings for natural speech
        self.use_ssml = True
        self.prosody_rate = "120%"  # 120% = 1.2x speed (can also use: x-slow, slow, medium, fast, x-fast)
        self.prosody_pitch = "medium"  # x-low, low, medium, high, x-high
        self.prosody_volume = "medium"  # silent, x-soft, soft, medium, loud, x-loud
        self.current_emotion = "neutral"
        self.base_speed_multiplier = 1.0
        
    def _add_ssml_prosody(self, text: str) -> str:
        """
        Wrap text in SSML tags for more natural, expressive speech.
        
        Args:
            text: Plain text to enhance
            
        Returns:
            SSML-wrapped text
        """
        if not self.use_ssml:
            return text
        
        # Add natural pauses after punctuation
        enhanced_text = text
        
        # Add slight pauses after commas
        enhanced_text = enhanced_text.replace(", ", ', <break time="200ms"/> ')
        
        # Add medium pauses after periods, questions, exclamations
        enhanced_text = enhanced_text.replace(". ", '. <break time="400ms"/> ')
        enhanced_text = enhanced_text.replace("? ", '? <break time="400ms"/> ')
        enhanced_text = enhanced_text.replace("! ", '! <break time="300ms"/> ')
        
        # Add emphasis to words in ALL CAPS
        import re
        def add_emphasis(match):
            word = match.group(0)
            return f'<emphasis level="strong">{word.lower()}</emphasis>'
        
        enhanced_text = re.sub(r'\b[A-Z]{2,}\b', add_emphasis, enhanced_text)
        
        # Wrap in speak and prosody tags
        ssml = f'''<speak>
            <prosody rate="{self.prosody_rate}" pitch="{self.prosody_pitch}" volume="{self.prosody_volume}">
                {enhanced_text}
            </prosody>
        </speak>'''
        
        return ssml
    
    # Voice Map for NVIDIA Riva
    VOICE_MAP = {
        "Aria": "Magpie-Multilingual.EN-US.Aria",
        "Diego": "Magpie-Multilingual.EN-US.Diego",
        "Jason": "Magpie-Multilingual.EN-US.Jason",
        "Leo": "Magpie-Multilingual.EN-US.Leo",
        "Mia": "Magpie-Multilingual.EN-US.Mia",
        "Isabela (ES Accent)": "Magpie-Multilingual.EN-US.Isabela",
        "Louise (FR Accent)": "Magpie-Multilingual.EN-US.Louise",
        "Pascal (FR Accent)": "Magpie-Multilingual.EN-US.Pascal",
    }
    
    def set_emotion(self, emotion: str):
        """
        Set the emotional tone of the voice.
        
        Args:
            emotion: One of 'neutral', 'happy', 'sad', 'excited', 'calm'
        """
        # Base settings for emotions
        emotion_settings = {
            'neutral': {'pitch': 'medium', 'volume': 'medium', 'rate_mod': 1.0},
            'happy': {'pitch': 'high', 'volume': 'loud', 'rate_mod': 1.1},
            'sad': {'pitch': 'low', 'volume': 'soft', 'rate_mod': 0.8},
            'excited': {'pitch': 'high', 'volume': 'x-loud', 'rate_mod': 1.2},
            'calm': {'pitch': 'low', 'volume': 'soft', 'rate_mod': 0.9},
            'serious': {'pitch': 'low', 'volume': 'medium', 'rate_mod': 0.9},
        }
        
        settings = emotion_settings.get(emotion, emotion_settings['neutral'])
        self.prosody_pitch = settings['pitch']
        self.prosody_volume = settings['volume']
        self.current_emotion = emotion
        
        # Recalculate rate based on base speed * emotion modifier
        # We need to store current base speed if we haven't
        if not hasattr(self, 'base_speed_multiplier'):
            self.base_speed_multiplier = 1.0
            
        final_speed = self.base_speed_multiplier * settings['rate_mod']
        self.prosody_rate = f"{int(final_speed * 100)}%"
        
        if config.DEBUG:
            print(f"🎭 [NVIDIA] Emotion set to: {emotion}")

    def set_speed(self, speed_multiplier: float):
        """
        Set speech speed multiplier.
        
        Args:
            speed_multiplier: 0.5 to 2.0 (1.0 is normal)
        """
        self.base_speed_multiplier = speed_multiplier
        # Recalculate based on current emotion
        self.set_emotion(self.current_emotion) # Re-applies logic with new base speed
        
        if config.DEBUG:
            print(f"⏩ [NVIDIA] Speed set to: {speed_multiplier}x (Effective: {self.prosody_rate})")

    def set_voice(self, voice_name: str):
        """
        Set the active voice.
        
        Args:
            voice_name: Friendly name (e.g., "Aria")
        """
        if voice_name in self.VOICE_MAP:
            self.voice = self.VOICE_MAP[voice_name]
            if config.DEBUG:
                print(f"🗣️ [NVIDIA] Voice set to: {voice_name} ({self.voice})")
        else:
            print(f"[WARN] Unknown voice: {voice_name}")

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech audio using NVIDIA Riva.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            WAV audio bytes or None if failed
        """
        if not text.strip():
            return None
            
        try:
            # Apply SSML enhancement for natural speech
            ssml_text = self._add_ssml_prosody(text)
            
            # Synthesize using Riva
            responses = self.tts_service.synthesize(
                text=ssml_text,
                voice_name=self.voice,
                language_code=self.language,
                sample_rate_hz=22050,
                encoding=riva.client.AudioEncoding.LINEAR_PCM
            )
            
            # Get audio data
            audio_data = responses.audio
            
            if config.DEBUG:
                print(f"🔊 [NVIDIA] Synthesized: {text[:50]}...")
            
            # Convert to WAV format
            wav_data = self._pcm_to_wav(audio_data, 22050)
            return wav_data
            
        except Exception as e:
            # If SSML fails, try without it
            if self.use_ssml and ("<speak>" in str(e) or "SSML" in str(e)):
                if config.DEBUG:
                    print("[WARN] SSML not supported/failed, falling back to plain text")
                # Temporarily disable SSML for retry
                original_ssml = self.use_ssml
                self.use_ssml = False
                res = self.synthesize(text)
                self.use_ssml = original_ssml
                return res
            print(f"[ERROR] NVIDIA TTS synthesis error: {e}")
            return None
    
    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 22050) -> bytes:
        """Convert raw PCM to WAV format."""
        import wave
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    def speak(self, text: str, blocking: bool = False) -> bool:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            blocking: If True, wait for playback to complete
            
        Returns:
            True if playback started successfully
        """
        if not text.strip():
            return False
            
        self.current_text = text
        self.spoken_text = ""
        
        # Synthesize audio
        audio_data = self.synthesize(text)
        
        if not audio_data:
            return False
        
        if blocking:
            return self._play_audio_blocking(audio_data, text)
        else:
            self.playback_thread = threading.Thread(
                target=self._play_audio_blocking,
                args=(audio_data, text),
                daemon=True
            )
            self.playback_thread.start()
            return True
    
    def speak_chunked(self, text: str) -> bool:
        """
        Speak text in sentence chunks for lower latency.
        
        Args:
            text: Full text to speak
            
        Returns:
            True if playback started successfully
        """
        if not text.strip():
            return False
            
        self.current_text = text
        self.spoken_text = ""
        self._should_stop = False
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return False
        
        self.playback_thread = threading.Thread(
            target=self._play_chunks,
            args=(sentences,),
            daemon=True
        )
        self.playback_thread.start()
        return True
    
    def _split_into_sentences(self, text: str) -> list:
        """Split text into sentences."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _play_chunks(self, sentences: list):
        """Play sentences one by one."""
        self._is_playing = True
        
        if self.on_playback_start:
            self.on_playback_start()
        
        try:
            for sentence in sentences:
                if self._should_stop:
                    if config.DEBUG:
                        print("⏹️ [NVIDIA] Playback interrupted")
                    break
                
                audio_data = self.synthesize(sentence)
                
                if audio_data and not self._should_stop:
                    self._play_audio_blocking(audio_data, sentence)
                    self.spoken_text += sentence + " "
                        
        finally:
            self._is_playing = False
            
            if self.on_playback_end:
                self.on_playback_end()
    
    def _play_audio_blocking(self, audio_data: bytes, text: str = "") -> bool:
        """Play audio and block until complete or interrupted."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                pygame.mixer.music.load(temp_file_path)
                pygame.mixer.music.play()
                
                self._is_playing = True
                
                while pygame.mixer.music.get_busy():
                    if self._should_stop:
                        pygame.mixer.music.stop()
                        return False
                    time.sleep(0.01)
                
                return True
                
            finally:
                pygame.mixer.music.unload()
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] [NVIDIA] Audio playback error: {e}")
            return False
        finally:
            self._is_playing = False
    
    def stop(self):
        """Stop current playback immediately."""
        self._should_stop = True
        
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        self._is_playing = False
        
        if config.DEBUG:
            print("⏹️ [NVIDIA] TTS stopped")
    
    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_playing or pygame.mixer.music.get_busy()
    
    def get_spoken_portion(self) -> str:
        """Get the portion of text spoken before interrupt."""
        return self.spoken_text.strip()
    
    def get_remaining_text(self) -> str:
        """Get unspoken portion of current text."""
        if not self.current_text or not self.spoken_text:
            return self.current_text
        spoken_len = len(self.spoken_text)
        if spoken_len < len(self.current_text):
            return self.current_text[spoken_len:].strip()
        return ""
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        try:
            self.channel.close()
        except:
            pass
        pygame.mixer.quit()
        
        if config.DEBUG:
            print("🔊 [NVIDIA] TTS cleaned up")
    
    def list_voices(self) -> list:
        """
        List available NVIDIA Riva voices.
        """
        return list(self.VOICE_MAP.keys())
