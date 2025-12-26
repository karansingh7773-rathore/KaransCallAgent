
import asyncio
import base64
import json
import os
from typing import Optional

# Conditional import for TextToSpeech
try:
    from modules import TextToSpeech
except ImportError:
    # Minimal mock if module is missing during initial setup debugging
    class TextToSpeech:
        def synthesize(self, text): return None

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
# Ensure modules are importable
sys.path.append('.')

# Import config and modules safely
# Import config and modules safely
try:
    from config import config
except ImportError:
    print("[CRITICAL] Failed to import config.py")
    sys.exit(1)

# Critical Modules
try:
    from modules import (
        AudioInput,
        SpeechToText,
        LLMHandler, 
        InterruptHandler,
        AssistantState
    )
except ImportError as e:
    print(f"[CRITICAL] Failed to import core modules: {e}")
    # We can't run without these
    sys.exit(1)

# Optional Modules
try:
    from modules import (
        NvidiaTTS,
        NVIDIA_TTS_AVAILABLE,
        NvidiaSpeechToText,
        NVIDIA_STT_AVAILABLE,
        WebSearchHandler
    )
except ImportError as e:
    print(f"[WARN] Optional modules issue: {e}")
    NVIDIA_TTS_AVAILABLE = False
    NVIDIA_STT_AVAILABLE = False

# Initialize FastAPI
app = FastAPI(title="Sentinel Connect API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Assistant Instance & Logic ---

class ServerVoiceAssistant:
    def __init__(self):
        # Initialize modules
        # STT
        if 'NvidiaSpeechToText' in globals() and NVIDIA_STT_AVAILABLE and config.NVIDIA_API_KEY:
            self.stt = NvidiaSpeechToText()
            self.stt_type = "nvidia"
            print("[Server] STT: NVIDIA Whisper")
        else:
            self.stt = SpeechToText()
            self.stt_type = "groq"
            print("[Server] STT: Groq Whisper")
            
        # LLM
        self.llm = LLMHandler()
        
        # TTS
        self.tts_provider = "groq" 
        self.tts = TextToSpeech() # Default
        
        if NVIDIA_TTS_AVAILABLE and config.NVIDIA_API_KEY:
             # Default to Nvidia if available
             try:
                 self.tts_provider = "nvidia"
                 self.tts = NvidiaTTS()
                 if hasattr(self.tts, 'set_emotion'):
                     self.tts.set_emotion('happy')
                 print("[Server] TTS: NVIDIA Riva")
             except Exception as e:
                 print(f"[Server] Failed to init NVIDIA TTS: {e}")
                 self.tts = TextToSpeech()

                 print(f"[Server] Failed to init NVIDIA TTS: {e}")
                 self.tts = TextToSpeech()

        # Voice Settings State
        self.current_speed = 1.0
        self.current_emotion = "neutral"
        # Current voice tracking is handled by the TTS instance, but we track if we need to restore
        
        self.interrupt_handler = InterruptHandler()
        
        # Prompt State
        self.current_agent_prompt = config.SYSTEM_PROMPT
        self.current_business_details = ""

    def update_prompt_config(self, agent_prompt=None, business_details=None):
        """Update the system prompt based on agent persona and business details."""
        if agent_prompt is not None:
            self.current_agent_prompt = agent_prompt
        if business_details is not None:
            self.current_business_details = business_details
            
        # Combine into effective system prompt
        full_prompt = self.current_agent_prompt
        if self.current_business_details:
            full_prompt += f"\n\nBusiness Context/Details:\n{self.current_business_details}"
            
        self.llm.update_system_prompt(full_prompt)
        print(f"[Server] Updated system prompt. Length: {len(full_prompt)}")

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        return self.stt.transcribe(audio_bytes)

    async def generate_response(self, text: str):
        return self.llm.generate_response(text)
    
    async def synthesize_audio(self, text: str) -> Optional[bytes]:
        return self.tts.synthesize(text)

    def switch_tts(self, provider: str):
        """Switch TTS provider dynamically."""
        provider = provider.lower()
        print(f"[Server] Switching TTS to: {provider}")
        
        # Cleanup existing TTS to release audio resources
        if hasattr(self, 'tts') and hasattr(self.tts, 'cleanup'):
            try:
                self.tts.cleanup()
            except Exception as e:
                print(f"[Warn] TTS cleanup failed: {e}")

        if provider == "nvidia" and NVIDIA_TTS_AVAILABLE and config.NVIDIA_API_KEY:
            try:
                self.tts = NvidiaTTS()
                if hasattr(self.tts, 'set_emotion'):
                    self.tts.set_emotion(self.current_emotion)
                if hasattr(self.tts, 'set_speed'):
                    self.tts.set_speed(self.current_speed)
                self.tts_provider = "nvidia"
                return True
            except Exception as e:
                print(f"[Server] Failed to switch to NVIDIA TTS: {e}")
                return False
        
        elif provider == "groq":
            self.tts = TextToSpeech()
            if hasattr(self.tts, 'set_speed'):
                self.tts.set_speed(self.current_speed)
            self.tts_provider = "groq"
            return True
            
        return False
        
    def update_voice_config(self, voice=None, speed=None, emotion=None):
        """Update voice settings."""
        if speed is not None:
            try:
                self.current_speed = float(speed)
                if hasattr(self.tts, 'set_speed'):
                    self.tts.set_speed(self.current_speed)
            except ValueError:
                pass
                
        if emotion is not None:
            self.current_emotion = emotion
            if hasattr(self.tts, 'set_emotion'):
                self.tts.set_emotion(emotion)
                
        if voice is not None:
            if hasattr(self.tts, 'set_voice'):
                self.tts.set_voice(voice)
                
    def get_available_voices(self):
        """Get list of voices for current provider."""
        if hasattr(self.tts, 'list_voices'):
            return self.tts.list_voices()
        return []

# Initialize Assistant
try:
    assistant = ServerVoiceAssistant()
except Exception as e:
    print(f"[CRITICAL] Failed to initialize assistant: {e}")
    assistant = None

# --- Routes ---

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Text-only chat endpoint."""
    if not assistant:
        return {"error": "Assistant not initialized"}
    response_text = assistant.llm.generate_response(request.message)
    return {"response": response_text}

# --- LiveKit Token Generation ---

class TokenRequest(BaseModel):
    identity: str = "user"
    room: str = "voice-assistant"

@app.post("/api/livekit-token")
async def get_livekit_token(request: TokenRequest):
    """Generate a LiveKit room access token for the frontend."""
    try:
        from livekit.api import AccessToken, VideoGrants
        
        livekit_url = os.getenv("LIVEKIT_URL", "")
        api_key = os.getenv("LIVEKIT_API_KEY", "")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        
        if not all([livekit_url, api_key, api_secret]):
            return {"error": "LiveKit not configured. Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in .env"}
        
        # Create access token using builder pattern (v1.1+ API)
        grant = VideoGrants(
            room_join=True,
            room=request.room,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )
        
        token = AccessToken(api_key, api_secret) \
            .with_identity(request.identity) \
            .with_name(request.identity) \
            .with_grants(grant)
        
        jwt_token = token.to_jwt()
        
        return {
            "token": jwt_token,
            "url": livekit_url,
            "room": request.room
        }
    except ImportError:
        return {"error": "LiveKit not installed. Run: pip install livekit"}
    except Exception as e:
        return {"error": f"Token generation failed: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")
    
    if not assistant:
        await websocket.send_json({"type": "error", "data": "Server assistant failed to initialize"})
        await websocket.close()
        return

    # Send initial voice list
    voices = assistant.get_available_voices()
    print(f"[Server] Sending initial voice list: {voices}")
    await websocket.send_json({"type": "voice_list", "voices": voices})

    try:
        while True:
            # Expecting JSON: { "type": "text", "data": "..." }
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'text':
                user_text = message['data']
                print(f"[WS] Received Text: {user_text}")
                
            elif message['type'] == 'audio':
                # Handle Audio Data
                audio_b64 = message['data']
                print(f"[WS] Audio received: {len(audio_b64)} chars") # DEBUG LOG

                # Decode
                audio_bytes = base64.b64decode(audio_b64)
                
                # Transcribe
                try:
                    user_text = assistant.stt.transcribe(audio_bytes)
                    print(f"[WS] Transcribed: {user_text}")
                    
                    # 1. Check for usable text first
                    if not user_text.strip():
                         continue

                    # 2. Filter hallucinations
                    clean = user_text.lower().strip()
                    if any(x in clean for x in ["*sizzling*", "*audio*", "*video*"]):
                         continue
                         
                    # 3. Valid speech detected -> Interrupt previous playback
                    # Signal frontend to stop audio
                    await websocket.send_json({"type": "interrupt"})
                    # Stop backend TTS
                    if assistant.tts.is_playing:
                        assistant.tts.stop()
                    
                    # Filter hallucinations and noise
                    ignored_phrases = [
                        "*sizzling*", "*audio*", "*video*", "", " ", "you", "thank you", "thank you.",
                        "subtitles", "watching", "subscribe", "like and subscribe"
                    ]
                    
                    cleaned_text = user_text.lower().strip()
                    
                    # Check for exact matches in ignored phrases
                    if any(phrase in cleaned_text for phrase in ["*sizzling*", "*audio*", "*video*"]):
                         print(f"[WS] Ignored hallucination: {user_text}")
                         continue
                         
                    # Check for short noise or specific stop words
                    if len(cleaned_text) < 2 or cleaned_text in ignored_phrases:
                        print(f"[WS] Ignored noise/short text: {user_text}")
                        continue
                        
                except Exception as e:
                    print(f"[WS] Transcription error: {e}")
                    continue
            
            elif message['type'] == 'config':
                # Handle Configuration Changes
                if 'tts' in message:
                    success = assistant.switch_tts(message['tts'])
                    if success:
                        await websocket.send_json({"type": "config_ack", "tts": assistant.tts_provider})
                        # Send new voice list
                        voices = assistant.get_available_voices()
                        await websocket.send_json({"type": "voice_list", "voices": voices})
                
                # Handle Voice Config
                if any(k in message for k in ['voice', 'speed', 'emotion']):
                    assistant.update_voice_config(
                        voice=message.get('voice'),
                        speed=message.get('speed'),
                        emotion=message.get('emotion')
                    )
                    await websocket.send_json({"type": "config_ack", "msg": "Voice settings updated"})
                
                # Handle Prompt Config
                if 'agent_prompt' in message or 'business_details' in message:
                    assistant.update_prompt_config(
                        agent_prompt=message.get('agent_prompt'), 
                        business_details=message.get('business_details')
                    )
                    await websocket.send_json({"type": "config_ack", "msg": "Prompt updated"})
                continue

            else:
                continue

            # --- Common Processing for Text & Audio (once we have text) ---
            
            # 1. State: PROCESSING
            await websocket.send_json({"type": "state", "data": "PROCESSING"})
            
            # 2. LLM Response
            response_text = assistant.llm.generate_response(user_text)
            
            # 3. Send Transcript
            await websocket.send_json({"type": "transcript", "role": "assistant", "data": response_text})
            
            # 4. State: SPEAKING
            await websocket.send_json({"type": "state", "data": "SPEAKING"})
            
            # 5. TTS Synthesis
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(None, assistant.tts.synthesize, response_text)
            
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                await websocket.send_json({"type": "audio", "data": audio_b64})
            
            # 6. State: IDLE
            await websocket.send_json({"type": "state", "data": "IDLE"})

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
