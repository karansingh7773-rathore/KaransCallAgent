"""
Audio Input Module - Captures microphone audio with Voice Activity Detection.
Uses WebRTC VAD for reliable speech detection.
"""

import pyaudio
import threading
import queue
import time
import webrtcvad
from typing import Optional, Callable
from collections import deque

import sys
sys.path.append('..')
from config import config


class AudioInput:
    """
    Handles microphone input with Voice Activity Detection (VAD).
    
    Features:
    - Real-time audio capture from microphone
    - WebRTC-based Voice Activity Detection
    - Circular buffer for audio storage
    - Callbacks for speech start/end events
    """
    
    def __init__(self):
        """Initialize the audio input module."""
        self.sample_rate = config.SAMPLE_RATE
        self.channels = config.CHANNELS
        self.chunk_size = config.CHUNK_SIZE
        self.format = pyaudio.paInt16
        
        # VAD setup
        self.vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
        
        # Frame duration for VAD (must be 10, 20, or 30 ms)
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        # Audio interface
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        
        # Threading and state
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        
        # Audio buffers
        self.audio_buffer = deque(maxlen=int(30 * 1000 / self.frame_duration_ms))  # 30 seconds max
        self.current_speech_buffer = []
        
        # Speech detection state
        self._is_speaking = False
        self.speech_start_time: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        
        # Ring buffer for VAD smoothing (prevents flicker)
        self.vad_buffer = deque(maxlen=10)  # ~300ms of VAD decisions
        
        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable[[bytes], None]] = None
        self.on_audio_level: Optional[Callable[[float], None]] = None
        
        # Queue for passing audio to main thread
        self.speech_queue = queue.Queue()
        
        # Mute state (to prevent echo when TTS is playing)
        self._muted = False
        self._mute_lock = threading.Lock()
        
    def start(self) -> bool:
        """
        Start capturing audio from the microphone.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            return True
            
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frame_size,
            )
            
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            if config.DEBUG:
                print("[OK] Audio input started")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to start audio input: {e}")
            return False
    
    def stop(self):
        """Stop audio capture and clean up resources."""
        self.is_running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
            self.capture_thread = None
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if config.DEBUG:
            print("[OK] Audio input stopped")
    
    def _capture_loop(self):
        """Main capture loop running in a separate thread."""
        while self.is_running:
            try:
                # Read audio frame
                frame = self.stream.read(self.frame_size, exception_on_overflow=False)
                
                # Check if frame contains speech using VAD
                # Skip speech detection if muted (prevents echo)
                with self._mute_lock:
                    if self._muted:
                        # Still store in buffer but don't detect speech
                        self.audio_buffer.append(frame)
                        continue
                
                is_speech = self._detect_speech(frame)
                
                # Smooth VAD decisions
                self.vad_buffer.append(is_speech)
                smoothed_speech = sum(self.vad_buffer) > len(self.vad_buffer) * 0.3
                
                current_time = time.time()
                
                if smoothed_speech:
                    self.last_speech_time = current_time
                    
                    if not self._is_speaking:
                        # Speech just started
                        self._is_speaking = True
                        self.speech_start_time = current_time
                        self.current_speech_buffer = []
                        
                        if self.on_speech_start:
                            self.on_speech_start()
                            
                        if config.DEBUG:
                            print("🗣️ Speech started")
                    
                    # Add frame to current speech buffer
                    self.current_speech_buffer.append(frame)
                    
                elif self._is_speaking:
                    # Still add frames during short pauses
                    self.current_speech_buffer.append(frame)
                    
                    # Check if silence threshold exceeded
                    silence_duration = (current_time - self.last_speech_time) * 1000
                    
                    if silence_duration >= config.SILENCE_THRESHOLD_MS:
                        # Speech ended
                        self._is_speaking = False
                        
                        # Check minimum speech duration
                        speech_duration = (current_time - self.speech_start_time) * 1000
                        
                        if speech_duration >= config.MIN_SPEECH_MS:
                            # Combine all frames into single audio chunk
                            audio_data = b''.join(self.current_speech_buffer)
                            
                            # Put in queue and call callback
                            self.speech_queue.put(audio_data)
                            
                            if self.on_speech_end:
                                self.on_speech_end(audio_data)
                                
                            if config.DEBUG:
                                print(f"🗣️ Speech ended ({speech_duration:.0f}ms)")
                        else:
                            if config.DEBUG:
                                print(f"⏭️ Speech too short ({speech_duration:.0f}ms), ignoring")
                        
                        self.current_speech_buffer = []
                        self.speech_start_time = None
                
                # Store in main buffer
                self.audio_buffer.append(frame)
                
            except Exception as e:
                if self.is_running:
                    print(f"[WARN] Audio capture error: {e}")
                    time.sleep(0.1)
    
    def _detect_speech(self, frame: bytes) -> bool:
        """
        Detect if audio frame contains speech using WebRTC VAD.
        
        Args:
            frame: Audio frame bytes
            
        Returns:
            True if speech detected, False otherwise
        """
        try:
            # WebRTC VAD requires specific frame sizes
            # Ensure frame is the right size
            if len(frame) == self.frame_size * 2:  # 2 bytes per sample (16-bit)
                return self.vad.is_speech(frame, self.sample_rate)
            return False
        except Exception:
            return False
    
    @property
    def is_speaking(self) -> bool:
        """Check if user is currently speaking."""
        return self._is_speaking and not self._muted
    
    @property
    def muted(self) -> bool:
        """Check if audio input is muted (ignoring speech detection)."""
        with self._mute_lock:
            return self._muted
    
    @muted.setter
    def muted(self, value: bool):
        """
        Set mute state. When muted, speech detection is disabled.
        Used to prevent echo when TTS is playing through speakers.
        
        Args:
            value: True to mute, False to unmute
        """
        with self._mute_lock:
            self._muted = value
            if value:
                # Clear any pending speech detection when muting
                self._is_speaking = False
                self.vad_buffer.clear()
                self.current_speech_buffer = []
                if config.DEBUG:
                    print("🔇 Microphone muted (echo prevention)")
            else:
                if config.DEBUG:
                    print("🔊 Microphone unmuted")
    
    def get_speech(self, timeout: float = 0.1) -> Optional[bytes]:
        """
        Get captured speech audio from the queue.
        
        Args:
            timeout: How long to wait for speech (seconds)
            
        Returns:
            Audio bytes if speech available, None otherwise
        """
        try:
            return self.speech_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_buffer(self):
        """Clear all audio buffers."""
        self.audio_buffer.clear()
        self.current_speech_buffer = []
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_audio_level(self) -> float:
        """
        Get the current audio input level (0.0 to 1.0).
        
        Returns:
            Audio level as a float
        """
        if not self.audio_buffer:
            return 0.0
            
        # Get the most recent frame
        recent_frame = self.audio_buffer[-1] if self.audio_buffer else b''
        
        if not recent_frame:
            return 0.0
            
        # Calculate RMS
        import numpy as np
        audio_array = np.frombuffer(recent_frame, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio_array ** 2))
        
        # Normalize (max int16 is 32767)
        return min(1.0, rms / 32767.0 * 10)  # Amplify for visibility
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        self.audio.terminate()
