"""
Text-to-Speech Module - Converts text to speech using Groq's PlayAI TTS.
Supports chunked playback for low latency and interrupt capability.
"""

import io
import os
import tempfile
import threading
import queue
import time
from typing import Optional, Callable
import pygame
from groq import Groq

import sys
sys.path.append('..')
from config import config



class TextToSpeech:
    """
    Handles text-to-speech conversion and playback using Groq's PlayAI.
    
    Features:
    - High-quality voice synthesis
    - Sentence-by-sentence chunking for faster first-word latency
    - Interruptible playback
    - Multiple voice options
    """
    
    # PlayAI Voice Map
    VOICE_MAP = {
        "Aaliyah": "Aaliyah-PlayAI",
        "Adelaide": "Adelaide-PlayAI",
        "Angelo": "Angelo-PlayAI",
        "Arista": "Arista-PlayAI",
        "Atlas": "Atlas-PlayAI",
        "Basil": "Basil-PlayAI",
        "Briggs": "Briggs-PlayAI",
        "Calum": "Calum-PlayAI",
        "Celeste": "Celeste-PlayAI",
        "Indigo": "Indigo-PlayAI",
        "Nia": "Nia-PlayAI",
    }

    def __init__(self):
        """Initialize TTS with Groq client and audio playback."""
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.TTS_MODEL
        self.voice = config.TTS_VOICE
        self.speed = 1.0
        
        # Initialize pygame mixer for audio playback
        if not pygame.mixer.get_init():
             pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
        
        # Playback state
        self._is_playing = False
        self._should_stop = False
        self.playback_thread: Optional[threading.Thread] = None
        
        # Audio queue for chunked playback
        self.audio_queue = queue.Queue()
        
        # Callbacks
        self.on_playback_start: Optional[Callable] = None
        self.on_playback_end: Optional[Callable] = None
        self.on_chunk_played: Optional[Callable[[str], None]] = None
        
        # Currently speaking text
        self.current_text = ""
        self.spoken_text = ""
        
    def set_voice(self, voice_name: str):
        """Set the active voice."""
        if voice_name in self.VOICE_MAP:
            self.voice = self.VOICE_MAP[voice_name]
            if config.DEBUG:
                print(f"🗣️ [Groq] Voice set to: {voice_name}")
        else:
            print(f"[WARN] Unknown voice: {voice_name}")
            
    def set_speed(self, speed: float):
        """Set speech speed (0.5 to 2.0)."""
        self.speed = max(0.5, min(2.0, speed))
        if config.DEBUG:
            print(f"⏩ [Groq] Speed set to: {self.speed}x")
            
    def list_voices(self) -> list:
        """List available voices."""
        return list(self.VOICE_MAP.keys())
        
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            WAV audio bytes or None if failed
        """
        if not text.strip():
            return None
            
        try:
            # Note: Groq API speed param documentation varies, but PlayAI model usually accepts it.
            # If not supported by specific endpoint version, it might be ignored or error.
            # We'll try passing it if supported by the client lib.
            
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="wav",
                speed=self.speed
            )
            
            # Get audio bytes from response
            audio_data = response.read()
            
            if config.DEBUG:
                print(f"🔊 Synthesized: {text[:50]}...")
            
            return audio_data
            
        except Exception as e:
            print(f"[ERROR] TTS synthesis error: {e}")
            return None
    
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
            # Start playback in background thread
            self.playback_thread = threading.Thread(
                target=self._play_audio_blocking,
                args=(audio_data, text),
                daemon=True
            )
            self.playback_thread.start()
            return True
    
    def speak_chunked(self, text: str) -> bool:
        """
        Speak text in sentence chunks for lower first-word latency.
        Synthesizes and plays sentences one by one.
        
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
        
        # Start chunked playback in background
        self.playback_thread = threading.Thread(
            target=self._play_chunks,
            args=(sentences,),
            daemon=True
        )
        self.playback_thread.start()
        return True
    
    def _split_into_sentences(self, text: str) -> list:
        """
        Split text into sentences for chunked playback.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        import re
        
        # Split on sentence endings, keeping the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter empty strings and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _play_chunks(self, sentences: list):
        """
        Play sentences one by one with synthesis pipelining.
        
        Args:
            sentences: List of sentences to speak
        """
        self._is_playing = True
        
        if self.on_playback_start:
            self.on_playback_start()
        
        try:
            for sentence in sentences:
                if self._should_stop:
                    if config.DEBUG:
                        print("⏹️ Playback interrupted")
                    break
                
                # Synthesize this sentence
                audio_data = self.synthesize(sentence)
                
                if audio_data and not self._should_stop:
                    self._play_audio_blocking(audio_data, sentence)
                    self.spoken_text += sentence + " "
                    
                    if self.on_chunk_played:
                        self.on_chunk_played(sentence)
                        
        finally:
            self._is_playing = False
            
            if self.on_playback_end:
                self.on_playback_end()
    
    def _play_audio_blocking(self, audio_data: bytes, text: str = "") -> bool:
        """
        Play audio data and block until complete or interrupted.
        
        Args:
            audio_data: WAV audio bytes
            text: Associated text (for tracking)
            
        Returns:
            True if played completely, False if interrupted
        """
        try:
            # Save to temp file for pygame
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Load and play
                pygame.mixer.music.load(temp_file_path)
                pygame.mixer.music.play()
                
                self._is_playing = True
                
                # Wait for playback to complete or stop signal
                while pygame.mixer.music.get_busy():
                    if self._should_stop:
                        pygame.mixer.music.stop()
                        return False
                    time.sleep(0.01)
                
                return True
                
            finally:
                # Clean up temp file
                pygame.mixer.music.unload()
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] Audio playback error: {e}")
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
            print("⏹️ TTS stopped")
    
    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_playing or pygame.mixer.music.get_busy()
    
    def get_spoken_portion(self) -> str:
        """
        Get the portion of text that was successfully spoken.
        Useful for tracking what was said before interrupt.
        
        Returns:
            Text that was spoken
        """
        return self.spoken_text.strip()
    
    def get_remaining_text(self) -> str:
        """
        Get the unspoken portion of the current text.
        
        Returns:
            Text that wasn't spoken yet
        """
        if not self.current_text or not self.spoken_text:
            return self.current_text
            
        # Find where we left off
        spoken_len = len(self.spoken_text)
        if spoken_len < len(self.current_text):
            return self.current_text[spoken_len:].strip()
        return ""
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        pygame.mixer.quit()
        
        if config.DEBUG:
            print("🔊 TTS cleaned up")


class TextToSpeechStreaming(TextToSpeech):
    """
    Extended TTS with streaming LLM response handling.
    Synthesizes and plays text as it streams from the LLM.
    """
    
    def __init__(self):
        """Initialize streaming TTS."""
        super().__init__()
        self.buffer = ""
        self.min_chunk_size = 50  # Minimum characters before synthesizing
        
    def speak_streaming(self, text_generator) -> bool:
        """
        Speak text as it streams from a generator.
        Buffers text until sentence boundaries or minimum size.
        
        Args:
            text_generator: Generator yielding text chunks
            
        Returns:
            True if completed successfully
        """
        self._should_stop = False
        self._is_playing = True
        self.buffer = ""
        self.spoken_text = ""
        
        if self.on_playback_start:
            self.on_playback_start()
        
        try:
            for chunk in text_generator:
                if self._should_stop:
                    break
                    
                self.buffer += chunk
                
                # Check for sentence boundaries
                sentences = self._extract_complete_sentences()
                
                for sentence in sentences:
                    if self._should_stop:
                        break
                        
                    audio_data = self.synthesize(sentence)
                    if audio_data:
                        self._play_audio_blocking(audio_data, sentence)
                        self.spoken_text += sentence + " "
            
            # Speak any remaining buffer
            if self.buffer.strip() and not self._should_stop:
                audio_data = self.synthesize(self.buffer.strip())
                if audio_data:
                    self._play_audio_blocking(audio_data, self.buffer.strip())
                    self.spoken_text += self.buffer.strip()
                self.buffer = ""
            
            return not self._should_stop
            
        finally:
            self._is_playing = False
            
            if self.on_playback_end:
                self.on_playback_end()
    
    def _extract_complete_sentences(self) -> list:
        """
        Extract complete sentences from buffer.
        
        Returns:
            List of complete sentences
        """
        import re
        
        sentences = []
        
        # Find sentence endings
        pattern = r'([^.!?]*[.!?])\s*'
        matches = re.findall(pattern, self.buffer)
        
        for match in matches:
            sentences.append(match.strip())
            self.buffer = self.buffer.replace(match, '', 1).strip()
        
        return sentences
