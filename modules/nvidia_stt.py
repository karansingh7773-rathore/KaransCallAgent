"""
NVIDIA Riva Speech-to-Text Module - Uses NVIDIA's Whisper API for transcription.
Optimized for low latency with gRPC streaming.
"""

import io
import os
import tempfile
import grpc
from typing import Optional

import sys
sys.path.append('..')
from config import config
from utils.audio_utils import audio_to_wav_bytes

# Check if NVIDIA Riva client is available
try:
    import riva.client
    NVIDIA_RIVA_AVAILABLE = True
except ImportError:
    NVIDIA_RIVA_AVAILABLE = False


class NvidiaSpeechToText:
    """
    Handles speech-to-text conversion using NVIDIA Riva Whisper API.
    
    Features:
    - whisper-large-v3 model via NVIDIA cloud
    - Multiple audio format support
    - Language detection or specification
    """
    
    # NVIDIA Whisper function ID
    FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"
    SERVER = "grpc.nvcf.nvidia.com:443"
    
    def __init__(self):
        """Initialize the NVIDIA STT module."""
        if not NVIDIA_RIVA_AVAILABLE:
            raise ImportError("nvidia-riva-client is not installed. Run: pip install nvidia-riva-client")
        
        if not config.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY is not set in environment variables")
        
        # Set up authentication
        self.metadata = [
            ("function-id", self.FUNCTION_ID),
            ("authorization", f"Bearer {config.NVIDIA_API_KEY}")
        ]
        
        # Create Riva Auth object with correct parameters for NVCF
        self.auth = riva.client.Auth(
            uri=self.SERVER,
            use_ssl=True,
            metadata_args=self.metadata
        )
        
        # Create ASR service
        self.asr_service = riva.client.ASRService(self.auth)
        self.language = "en-US"
        
    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe audio bytes to text using NVIDIA Whisper.
        
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
            
            # Configure recognition
            recognition_config = riva.client.RecognitionConfig(
                language_code=self.language,
                max_alternatives=1,
                enable_automatic_punctuation=True,
                audio_channel_count=1,
            )
            
            # Perform offline recognition
            response = self.asr_service.offline_recognize(
                wav_data,
                recognition_config
            )
            
            # Extract text from response
            if response.results:
                text = ""
                for result in response.results:
                    if result.alternatives:
                        text += result.alternatives[0].transcript
                
                text = text.strip()
                
                if config.DEBUG:
                    print(f"[DEBUG] Transcribed: {text}")
                
                return text if text else None
            
            return None
                
        except Exception as e:
            print(f"[ERROR] Transcription error: {e}")
            return None
    
    def transcribe_streaming(self, audio_chunks, sample_rate: int = 16000):
        """
        Stream transcribe audio chunks in real-time.
        
        Args:
            audio_chunks: Iterator of audio chunk bytes
            sample_rate: Audio sample rate
            
        Yields:
            Partial transcription strings
        """
        try:
            # Configure streaming recognition
            streaming_config = riva.client.StreamingRecognitionConfig(
                config=riva.client.RecognitionConfig(
                    language_code=self.language,
                    max_alternatives=1,
                    enable_automatic_punctuation=True,
                    audio_channel_count=1,
                ),
                interim_results=True
            )
            
            # Create generator for audio chunks
            def audio_generator():
                for chunk in audio_chunks:
                    yield chunk
            
            # Perform streaming recognition
            responses = self.asr_service.streaming_response_generator(
                audio_chunks=audio_generator(),
                streaming_config=streaming_config
            )
            
            for response in responses:
                for result in response.results:
                    if result.alternatives:
                        yield result.alternatives[0].transcript
                        
        except Exception as e:
            print(f"[ERROR] Streaming transcription error: {e}")
