"""
LiveKit Voice Agent for Sentinel Connect

Features:
- Silero VAD (Voice Activity Detection)
- Deepgram STT (Speech-to-Text) - Ultra fast
- Groq Llama LLM (Language Model)
- Deepgram Aura TTS (Text-to-Speech) - Low latency
- Dynamic voice switching via participant attributes

Run with: python livekit_agent.py dev
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, tts
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import deepgram, groq, silero

# Add modules to path for config
sys.path.append('.')
try:
    from config import config
    SYSTEM_PROMPT = config.SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = "You are a helpful voice assistant. Keep responses short and conversational."


# ============================================================
# Available Deepgram Aura Voices
# ============================================================

DEEPGRAM_VOICES = {
    # Aura-2 (Newest, recommended)
    "arcas": "aura-2-arcas-en",       # Male, deep
    "thalia": "aura-2-thalia-en",     # Female, warm
    "andromeda": "aura-2-andromeda-en", # Female, clear
    "orpheus": "aura-2-orpheus-en",   # Male, rich
    "luna": "aura-2-luna-en",         # Female, soft
    "atlas": "aura-2-atlas-en",       # Male, strong
    "orion": "aura-2-orion-en",       # Male, neutral
    "stella": "aura-2-stella-en",     # Female, bright
    # Aura-1 (Legacy)
    "asteria": "aura-asteria-en",     # Female
    "perseus": "aura-perseus-en",     # Male
    "hera": "aura-hera-en",           # Female
    "zeus": "aura-zeus-en",           # Male
}

DEFAULT_VOICE = "arcas"


# ============================================================
# Switchable TTS - Supports dynamic voice switching
# ============================================================

class SwitchableTTS(tts.TTS):
    """TTS wrapper that can switch Deepgram voices in real-time."""
    
    def __init__(self, initial_voice: str = DEFAULT_VOICE):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=24000,
            num_channels=1,
        )
        
        self.current_voice = initial_voice
        self._update_tts()
        print(f"[TTS] Deepgram Aura initialized with voice: {self.current_voice}")
    
    def _update_tts(self):
        """Create Deepgram TTS with current voice."""
        model = DEEPGRAM_VOICES.get(self.current_voice, DEEPGRAM_VOICES[DEFAULT_VOICE])
        self._tts = deepgram.TTS(model=model)
        print(f"[TTS] Using model: {model}")
    
    def update_voice(self, voice: str):
        """Switch voice (called when frontend changes settings)."""
        voice = voice.lower()
        if voice in DEEPGRAM_VOICES:
            self.current_voice = voice
            self._update_tts()
            print(f"[TTS] Switched voice to: {voice}")
        else:
            print(f"[TTS] Unknown voice: {voice}, keeping {self.current_voice}")
    
    def synthesize(self, text: str, *, conn_options=None) -> tts.ChunkedStream:
        """Synthesize text with current voice."""
        print(f"[TTS] Synthesizing with {self.current_voice}: '{text[:50]}...'")
        return self._tts.synthesize(text)
    
    def stream(self, *, conn_options=None) -> tts.SynthesizeStream:
        """Stream synthesis with current voice."""
        return self._tts.stream()


# ============================================================
# Voice Agent
# ============================================================

class SentinelAgent(Agent):
    """Voice agent using Deepgram STT/TTS and Groq LLM."""
    
    def __init__(self):
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )
    
    async def on_enter(self) -> None:
        """Send greeting when session starts."""
        print("[Agent] Session started, sending greeting...")
        await self.session.say(
            "Hello! I'm your voice assistant. How can I help you today?",
            allow_interruptions=True
        )


# ============================================================
# Entry Point
# ============================================================

async def entrypoint(ctx: JobContext):
    """Main agent entry point."""
    
    print(f"[Agent] Room: {ctx.room.name}, waiting for participant...")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    participant = await ctx.wait_for_participant()
    print(f"[Agent] Participant joined: {participant.identity}")
    
    # Create switchable TTS with Deepgram voices
    switchable_tts = SwitchableTTS(initial_voice=DEFAULT_VOICE)
    
    # Create agent session
    session = AgentSession(
        vad=silero.VAD.load(),
        
        # Deepgram for STT (ultra-fast Whisper)
        stt=deepgram.STT(),
        
        # Groq for LLM (fast Llama)
        llm=groq.LLM(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        ),
        
        # Deepgram for TTS (low-latency Aura)
        tts=switchable_tts,
        
        allow_interruptions=True,
    )
    
    # Listen for voice changes from frontend
    @ctx.room.on("participant_attributes_changed")
    def on_attributes_changed(changed_attributes: dict, participant):
        """Handle frontend voice switch."""
        if "tts_voice" in changed_attributes:
            new_voice = participant.attributes.get("tts_voice", DEFAULT_VOICE)
            switchable_tts.update_voice(new_voice)
            print(f"[Agent] Frontend requested voice switch to: {new_voice}")
    
    # Check initial attributes
    if participant.attributes:
        initial_voice = participant.attributes.get("tts_voice", DEFAULT_VOICE)
        switchable_tts.update_voice(initial_voice)
    
    agent = SentinelAgent()
    
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    print("[Agent] Session started, listening for speech...")
    print(f"[Agent] Available voices: {list(DEEPGRAM_VOICES.keys())}")


def prewarm(proc: JobProcess):
    """Prewarm VAD model."""
    print("[Agent] Prewarming VAD...")
    proc.userdata["vad"] = silero.VAD.load()
    print("[Agent] Prewarm complete")


if __name__ == "__main__":
    print("[Agent] Starting Sentinel Connect Voice Agent...")
    print(f"[Agent] LiveKit URL: {os.getenv('LIVEKIT_URL', 'NOT SET')}")
    print(f"[Agent] Deepgram API Key: {'SET' if os.getenv('DEEPGRAM_API_KEY') else 'NOT SET'}")
    print(f"[Agent] Groq API Key: {'SET' if os.getenv('GROQ_API_KEY') else 'NOT SET'}")
    print(f"[Agent] Available voices: {list(DEEPGRAM_VOICES.keys())}")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
