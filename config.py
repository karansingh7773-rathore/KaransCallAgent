"""
Configuration settings for the Voice Assistant.
Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration for the voice assistant."""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Model Settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    STT_MODEL: str = os.getenv("STT_MODEL", "whisper-large-v3")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "playai-tts")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "Ruby-PlayAI")
    
    # NVIDIA Riva TTS Settings
    NVIDIA_TTS_SERVER: str = "grpc.nvcf.nvidia.com:443"
    NVIDIA_TTS_FUNCTION_ID: str = "877104f7-e885-42b9-8de8-f6e4c6303969"
    NVIDIA_TTS_VOICE: str = os.getenv("NVIDIA_TTS_VOICE", "Magpie-Multilingual.EN-US.Mia")
    NVIDIA_TTS_LANGUAGE: str = os.getenv("NVIDIA_TTS_LANGUAGE", "en-US")
    
    # Audio Settings
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    CHANNELS: int = 1  # Mono audio
    CHUNK_SIZE: int = 480  # 30ms at 16kHz (16000 * 0.03 = 480)
    FORMAT_BYTES: int = 2  # 16-bit audio = 2 bytes per sample
    
    # VAD Settings
    VAD_AGGRESSIVENESS: int = int(os.getenv("VAD_AGGRESSIVENESS", "3"))  # 0-3, 3 is most aggressive
    
    # Silence detection
    SILENCE_THRESHOLD_MS: int = 700  # Consider speech ended after this much silence
    MIN_SPEECH_MS: int = 300  # Minimum speech duration to process
    
    # Interrupt detection
    INTERRUPT_THRESHOLD_MS: int = 200  # How long user must speak to trigger interrupt
    
    # System prompt for the assistant
    SYSTEM_PROMPT: str = """You are a helpful, friendly voice assistant. Keep your responses concise and conversational since they will be spoken aloud. 

Key behaviors:
- Be natural and human-like in your responses
- Keep answers brief but informative (1-3 sentences when possible)
- If you were interrupted and the user went silent, ask them politely to continue
- Use casual language appropriate for voice conversation
- Avoid using markdown, bullet points, or formatting that doesn't work in speech
- Don't use emojis or special characters

Remember: You're having a voice conversation, not writing text."""

    # Resume prompts when user interrupts then goes silent
    RESUME_PROMPTS: list = [
        "Yes? Go ahead, I'm listening.",
        "Sorry, what were you going to say?",
        "I'm all ears. Please continue.",
        "Yes, please go ahead.",
        "What's on your mind?",
        "I'm listening, please continue.",
    ]
    
    # Debug mode
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @classmethod
    def validate(cls, require_nvidia: bool = False) -> bool:
        """Validate that required configuration is present."""
        if not cls.GROQ_API_KEY:
            print("❌ Error: GROQ_API_KEY is not set!")
            print("   Please set it in your .env file or environment variables.")
            print("   Get your key from: https://console.groq.com/keys")
            return False
        
        if require_nvidia and not cls.NVIDIA_API_KEY:
            print("❌ Error: NVIDIA_API_KEY is not set!")
            print("   Please set it in your .env file or environment variables.")
            print("   Get your key from: https://build.nvidia.com/")
            return False
            
        return True


# Create a singleton config instance
config = Config()
