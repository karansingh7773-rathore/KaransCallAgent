"""
Voice Assistant Modules
"""

# Optional: AudioInput (requires pyaudio - not available on cloud servers)
try:
    from .audio_input import AudioInput
except ImportError:
    AudioInput = None

from .speech_to_text import SpeechToText
from .llm_handler import LLMHandler
from .text_to_speech import TextToSpeech
from .interrupt_handler import InterruptHandler, AssistantState
from .web_search import WebSearchHandler, TAVILY_AVAILABLE

# Optional: NVIDIA TTS (may not be available)
try:
    from .nvidia_tts import NvidiaTTS
    NVIDIA_TTS_AVAILABLE = True
except ImportError:
    NvidiaTTS = None
    NVIDIA_TTS_AVAILABLE = False

# Optional: NVIDIA STT (may not be available)
try:
    from .nvidia_stt import NvidiaSpeechToText
    NVIDIA_STT_AVAILABLE = True
except ImportError:
    NvidiaSpeechToText = None
    NVIDIA_STT_AVAILABLE = False

__all__ = [
    "AudioInput",
    "SpeechToText",
    "NvidiaSpeechToText",
    "LLMHandler",
    "TextToSpeech",
    "NvidiaTTS",
    "InterruptHandler",
    "AssistantState",
    "NVIDIA_TTS_AVAILABLE",
    "NVIDIA_STT_AVAILABLE",
    "WebSearchHandler",
    "TAVILY_AVAILABLE",
]
