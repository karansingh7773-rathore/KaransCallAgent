"""
LiveKit Voice Agent for Sentinel Connect

Features:
- Silero VAD (Voice Activity Detection)
- Deepgram STT (Speech-to-Text) - Ultra fast
- Groq Llama LLM (Language Model)
- Deepgram Aura TTS (Text-to-Speech) - Low latency
- Dynamic instructions from frontend attributes

Run with: .\venv\Scripts\python.exe livekit_agent.py dev
"""

import os
import sys
import logging
import asyncio

from dotenv import load_dotenv
load_dotenv()

# Imports for livekit-agents 1.3.10
from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, tts, llm
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import deepgram, groq, silero

# Setup logging
logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)

# Add modules to path for config
sys.path.append('.')
try:
    from config import config
    SYSTEM_PROMPT = config.SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = "You are a helpful voice assistant. Keep responses short and conversational."


# ============================================================
# Robust Deepgram Voice Switcher
# ============================================================

DEFAULT_VOICE = "arcas"

class DeepgramSwitcher(tts.TTS):
    """Robust TTS wrapper that supports voice switching without crashes."""
    
    def __init__(self):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=24000,
            num_channels=1
        )
        
        logger.info("Initializing Deepgram voice...")
        
        self.voices = {
            "arcas": deepgram.TTS(model="aura-2-arcas-en"),
        }
        
        self.current_voice_id = DEFAULT_VOICE
        logger.info(f"DeepgramSwitcher initialized with voice: {DEFAULT_VOICE}")
    
    def update_voice(self, voice_id: str):
        clean_id = voice_id.lower().strip()
        clean_id = clean_id.replace("aura-2-", "").replace("aura-", "").replace("-en", "")
        
        if clean_id in self.voices:
            old_voice = self.current_voice_id
            self.current_voice_id = clean_id
            print(f"[TTS] Voice switched: {old_voice} -> {clean_id}")
        else:
            logger.warning(f"Unknown voice '{voice_id}'. Keeping {self.current_voice_id}")
    
    def synthesize(self, text: str, *, conn_options=None) -> tts.ChunkedStream:
        try:
            active_tts = self.voices[self.current_voice_id]
            return active_tts.synthesize(text, conn_options=conn_options)
        except Exception as e:
            logger.error(f"TTS FAILED: {e}")
            return self.voices[DEFAULT_VOICE].synthesize(text, conn_options=conn_options)
    
    def stream(self, *, conn_options=None) -> tts.SynthesizeStream:
        try:
            active_tts = self.voices[self.current_voice_id]
            return active_tts.stream(conn_options=conn_options)
        except Exception as e:
            logger.error(f"TTS STREAM FAILED: {e}")
            return self.voices[DEFAULT_VOICE].stream(conn_options=conn_options)


# Default System Prompt (Apex Industries)
DEFAULT_SYSTEM_PROMPT = """You are Nio, a Calling Agent at Apex Industries working for Karan, who is the CEO of the company.
Apex Industries is a leader in Advanced Manufacturing with three main divisions:
1. Apex Automation (Robotic arms)
2. Apex Security (Surveillance)
3. Apex Health (Medical devices)

Your goal is to handle initial inquiries, screen potential B2B clients, and schedule appointments.
Keep responses short, professional, and business-like."""

# TTS Output Rules
TTS_INSTRUCTIONS = """
# Output Rules
- Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
- Keep replies brief by default: one to three sentences.
- Spell out numbers, phone numbers, or email addresses.
- Omit `https://` and other formatting if listing a web URL.
"""


# ============================================================
# Custom Agent (inherits from Agent to use built-in update_instructions)
# ============================================================

class SentinelAgent(Agent):
    """Voice agent that supports dynamic instruction updates."""
    
    def __init__(self, instructions: str):
        super().__init__(instructions=instructions)
        self._current_instructions = instructions
    
    async def on_enter(self) -> None:
        """Send greeting when session starts."""
        print("[Agent] Session started, sending greeting...")
        
        if "Apex Industries" in self._current_instructions:
            greeting = "Hello! I am Nio, a Calling Agent at Apex Industries. How can I assist you today?"
        else:
            greeting = "Hello! How can I help you today?"
            
        await self.session.say(greeting, allow_interruptions=True)
    
    def set_new_instructions(self, new_instructions: str):
        """Update instructions using the built-in Agent method."""
        self._current_instructions = new_instructions
        # Agent.update_instructions is ASYNC - must schedule it properly
        asyncio.create_task(super().update_instructions(new_instructions))
        print(f"[Agent] Instructions updated via Agent.update_instructions() - length: {len(new_instructions)}")


# ============================================================
# Helper Functions
# ============================================================

def get_instructions_from_attributes(attributes):
    """Build instructions from frontend attributes."""
    prompt = attributes.get("agent_prompt", "")
    business = attributes.get("business_details", "")
    
    # If BOTH are empty, use the full default persona
    if not prompt and not business:
        return DEFAULT_SYSTEM_PROMPT + TTS_INSTRUCTIONS
    
    # Build a custom structured prompt
    instructions_parts = []
    
    if prompt:
        instructions_parts.append(f"# Identity\n{prompt}")
    else:
        instructions_parts.append("# Identity\nYou are a helpful voice assistant.")
        
    if business:
        instructions_parts.append(f"# Business Context\n{business}")
        
    instructions_parts.append(TTS_INSTRUCTIONS)
    
    new_inst = "\n\n".join(instructions_parts)
    print(f"[Agent] Custom instructions built from attributes (length: {len(new_inst)})")
    return new_inst


# ============================================================
# Entry Point
# ============================================================

async def entrypoint(ctx: JobContext):
    """Main agent entry point."""
    
    print(f"[Agent] Room: {ctx.room.name}, waiting for participant...")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    participant = await ctx.wait_for_participant()
    print(f"[Agent] Participant joined: {participant.identity}")
    
    # Create the voice switcher
    voice_switcher = DeepgramSwitcher()
    
    # Storage for received attributes
    received_attributes = {}
    attributes_received = asyncio.Event()
    
    # Register attribute change listener BEFORE waiting
    @ctx.room.on("participant_attributes_changed")
    def on_initial_attributes(changed_attributes: dict, p):
        print(f"[Agent] Attribute change event: {list(changed_attributes.keys())}")
        received_attributes.update(p.attributes)
        if "agent_prompt" in changed_attributes or "business_details" in changed_attributes or "tts_voice" in changed_attributes:
            attributes_received.set()
    
    # FAST TIMEOUT: Wait max 1 second for initial attributes
    print("[Agent] Waiting for initial attributes (max 1s)...")
    
    # Check if attributes already exist
    if participant.attributes and ("agent_prompt" in participant.attributes or "business_details" in participant.attributes):
        received_attributes.update(participant.attributes)
        print("[Agent] Attributes found immediately")
    else:
        # Wait for attribute event OR poll every 100ms (whichever is first)
        try:
            await asyncio.wait_for(attributes_received.wait(), timeout=1.0)
            print("[Agent] Attributes received via event")
        except asyncio.TimeoutError:
            # Final check after timeout
            if participant.attributes:
                received_attributes.update(participant.attributes)
                print("[Agent] Attributes found after timeout")
            else:
                print("[Agent] Timeout - no attributes, using defaults")
    
    # Ensure we have the latest
    if participant.attributes:
        received_attributes.update(participant.attributes)
    
    print(f"[Agent] Final Attributes: {received_attributes}")
    
    # Determine initial instructions
    initial_instructions = DEFAULT_SYSTEM_PROMPT + TTS_INSTRUCTIONS
    if received_attributes:
        initial_instructions = get_instructions_from_attributes(received_attributes)
        
        initial_voice = received_attributes.get("tts_voice", DEFAULT_VOICE)
        if initial_voice != DEFAULT_VOICE:
            voice_switcher.update_voice(initial_voice)

    # Create agent session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=groq.LLM(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        ),
        tts=voice_switcher,
        allow_interruptions=True,
    )
    
    # Create the agent
    agent = SentinelAgent(instructions=initial_instructions)

    # Runtime attribute handler - uses Agent's built-in update_instructions
    @ctx.room.on("participant_attributes_changed")
    def on_runtime_attributes(changed_attributes: dict, p):
        print(f"[Agent] Runtime attribute change: {list(changed_attributes.keys())}")
        
        if "tts_voice" in changed_attributes:
            new_voice = p.attributes.get("tts_voice", DEFAULT_VOICE)
            voice_switcher.update_voice(new_voice)
            
        if "agent_prompt" in changed_attributes or "business_details" in changed_attributes:
            new_instructions = get_instructions_from_attributes(p.attributes)
            # Use our wrapper which calls Agent.update_instructions()
            agent.set_new_instructions(new_instructions)
    
    # Start the session
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    print("[Agent] Session started, listening...")


def prewarm(proc: JobProcess):
    """Prewarm VAD model for faster startup."""
    print("[Agent] Prewarming VAD...")
    proc.userdata["vad"] = silero.VAD.load()
    print("[Agent] Prewarm complete")


if __name__ == "__main__":
    print("[Agent] Starting Sentinel Connect Voice Agent...")
    print(f"[Agent] LiveKit URL: {os.getenv('LIVEKIT_URL', 'NOT SET')}")
    print(f"[Agent] Deepgram API Key: {'SET' if os.getenv('DEEPGRAM_API_KEY') else 'NOT SET'}")
    print(f"[Agent] Groq API Key: {'SET' if os.getenv('GROQ_API_KEY') else 'NOT SET'}")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
