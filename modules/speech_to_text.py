"""
Speech-to-Text Module - Converts audio to text using Groq's Whisper API.
Optimized for low latency with streaming-ready architecture.
"""

import io
import os
import tempfile
from typing import Optional
from groq import Groq

import sys
sys.path.append('..')
from config import config
from utils.audio_utils import audio_to_wav_bytes


class SpeechToText:
    """
    Handles speech-to-text conversion using Groq's Whisper API.
    
    Features:
    - Fast transcription with whisper-large-v3-turbo
    - Multiple audio format support
    - Language detection or specification
    """
    
    def __init__(self):
        """Initialize the STT module with Groq client."""
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.STT_MODEL
        self.language = "en"  # Specify language for faster processing
        
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit mono)
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Transcribed text or None if failed
        """
        if not audio_data:
            return None
            
        try:
            # Convert raw PCM to WAV format
            wav_data = audio_to_wav_bytes(audio_data, sample_rate)
            
            # Create a temporary file for the API
            # Groq API requires a file-like object with a name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                # Open and send to Groq API
                with open(temp_file_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=self.model,
                        language=self.language,
                        response_format="text",
                        temperature=0.0,  # More deterministic output
                    )
                
                # Extract text from response
                text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
                
                if config.DEBUG:
                    print(f"[DEBUG] Transcribed: {text}")
                
                return text if text else None
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] Transcription error: {e}")
            return None
    
    def transcribe_with_timestamps(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[dict]:
        """
        Transcribe audio with word-level timestamps.
        
        Args:
            audio_data: Raw PCM audio bytes
            sample_rate: Audio sample rate
            
        Returns:
            Dictionary with text and timestamps, or None if failed
        """
        if not audio_data:
            return None
            
        try:
            wav_data = audio_to_wav_bytes(audio_data, sample_rate)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=self.model,
                        language=self.language,
                        response_format="verbose_json",
                        timestamp_granularities=["word", "segment"],
                        temperature=0.0,
                    )
                
                return {
                    "text": transcription.text,
                    "words": transcription.words if hasattr(transcription, 'words') else [],
                    "segments": transcription.segments if hasattr(transcription, 'segments') else [],
                }
                
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] Transcription with timestamps error: {e}")
            return None


class SpeechToTextAsync:
    """
    Async version of Speech-to-Text for non-blocking operations.
    """
    
    def __init__(self):
        """Initialize async STT with Groq client."""
        from groq import AsyncGroq
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        self.model = config.STT_MODEL
        self.language = "en"
        
    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Async transcribe audio bytes to text.
        
        Args:
            audio_data: Raw PCM audio bytes
            sample_rate: Audio sample rate
            
        Returns:
            Transcribed text or None if failed
        """
        if not audio_data:
            return None
            
        try:
            wav_data = audio_to_wav_bytes(audio_data, sample_rate)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = await self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=self.model,
                        language=self.language,
                        response_format="text",
                        temperature=0.0,
                    )
                
                text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
                
                if config.DEBUG:
                    print(f"[DEBUG] Transcribed (async): {text}")
                
                return text if text else None
                
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] Async transcription error: {e}")
            return None
