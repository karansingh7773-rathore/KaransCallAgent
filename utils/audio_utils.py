"""
Audio utility functions for processing and converting audio data.
"""

import io
import wave
import numpy as np
from typing import Optional


def audio_to_wav_bytes(audio_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """
    Convert raw PCM audio bytes to WAV format.
    
    Args:
        audio_data: Raw PCM audio bytes (16-bit)
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        
    Returns:
        WAV file bytes
    """
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    
    wav_buffer.seek(0)
    return wav_buffer.read()


def normalize_audio(audio_data: bytes) -> bytes:
    """
    Normalize audio volume to prevent clipping and improve quality.
    
    Args:
        audio_data: Raw PCM audio bytes (16-bit)
        
    Returns:
        Normalized audio bytes
    """
    # Convert bytes to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    
    # Normalize to [-1, 1] range
    max_val = np.max(np.abs(audio_array))
    if max_val > 0:
        audio_array = audio_array / max_val
    
    # Scale back to int16 range with some headroom
    audio_array = (audio_array * 32000).astype(np.int16)
    
    return audio_array.tobytes()


def calculate_rms(audio_data: bytes) -> float:
    """
    Calculate the Root Mean Square (RMS) of audio data.
    Used for simple volume-based voice activity detection.
    
    Args:
        audio_data: Raw PCM audio bytes (16-bit)
        
    Returns:
        RMS value (0.0 to 1.0)
    """
    if not audio_data:
        return 0.0
        
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    
    if len(audio_array) == 0:
        return 0.0
    
    # Calculate RMS
    rms = np.sqrt(np.mean(audio_array ** 2))
    
    # Normalize to 0-1 range (max int16 value is 32767)
    normalized_rms = rms / 32767.0
    
    return float(normalized_rms)


def split_audio_frames(audio_data: bytes, frame_size: int) -> list:
    """
    Split audio data into frames of specified size.
    
    Args:
        audio_data: Raw PCM audio bytes
        frame_size: Size of each frame in bytes
        
    Returns:
        List of audio frames
    """
    frames = []
    for i in range(0, len(audio_data), frame_size):
        frame = audio_data[i:i + frame_size]
        if len(frame) == frame_size:
            frames.append(frame)
    return frames


def resample_audio(audio_data: bytes, original_rate: int, target_rate: int) -> bytes:
    """
    Resample audio to a different sample rate.
    
    Args:
        audio_data: Raw PCM audio bytes (16-bit)
        original_rate: Original sample rate
        target_rate: Target sample rate
        
    Returns:
        Resampled audio bytes
    """
    if original_rate == target_rate:
        return audio_data
    
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    
    # Calculate the number of samples in the resampled audio
    duration = len(audio_array) / original_rate
    new_length = int(duration * target_rate)
    
    # Linear interpolation for resampling
    old_indices = np.arange(len(audio_array))
    new_indices = np.linspace(0, len(audio_array) - 1, new_length)
    
    resampled = np.interp(new_indices, old_indices, audio_array).astype(np.int16)
    
    return resampled.tobytes()
