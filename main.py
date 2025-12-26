"""
Voice Assistant - Main Entry Point

A low-latency voice assistant with interrupt handling and conversation memory.
Uses NVIDIA and Groq AI APIs for:
- Speech-to-Text: NVIDIA Whisper (whisper-large-v3)
- LLM: Groq llama-3.3-70b-versatile
- Text-to-Speech: Groq PlayAI TTS OR NVIDIA Riva

Features:
- 0.2-0.5 second response latency target
- Interrupt detection during AI speech
- Natural conversation resumption after interrupts
- Conversation history for context
- Choice between Groq and NVIDIA TTS
"""

import sys
import time
import threading
from typing import Optional, Union

from config import config
from modules import (
    AudioInput,
    SpeechToText,
    LLMHandler, 
    TextToSpeech,
    InterruptHandler,
    AssistantState,
    NVIDIA_TTS_AVAILABLE,
    NVIDIA_STT_AVAILABLE,
)

# Conditionally import NVIDIA modules
if NVIDIA_TTS_AVAILABLE:
    from modules import NvidiaTTS

if NVIDIA_STT_AVAILABLE:
    from modules import NvidiaSpeechToText


def select_tts_provider() -> tuple:
    """
    Display menu for selecting TTS provider.
    
    Returns:
        Tuple of (provider_name, tts_instance)
    """
    print("\n" + "=" * 50)
    print("Voice Assistant - TTS Provider Selection")
    print("=" * 50)
    print()
    print("Choose your Text-to-Speech provider:")
    print()
    print("  [1] Groq PlayAI TTS")
    print(f"      Voice: {config.TTS_VOICE}")
    print("      Fast, high-quality neural TTS")
    print()
    
    if NVIDIA_TTS_AVAILABLE and config.NVIDIA_API_KEY:
        print("  [2] NVIDIA Riva TTS")
        print(f"      Voice: {config.NVIDIA_TTS_VOICE}")
        print("      Enterprise-grade multilingual TTS")
        print()
        valid_choices = ["1", "2"]
    else:
        print("  [2] NVIDIA Riva TTS (Not available)")
        if not NVIDIA_TTS_AVAILABLE:
            print("      [!] nvidia-riva-client not installed")
        elif not config.NVIDIA_API_KEY:
            print("      [!] NVIDIA_API_KEY not set in .env")
        print()
        valid_choices = ["1"]
    
    print("-" * 50)
    
    while True:
        try:
            choice = input("Enter your choice (1 or 2): ").strip()
            
            if choice == "1":
                print("\n[OK] Selected: Groq PlayAI TTS")
                return ("groq", TextToSpeech())
            
            elif choice == "2" and "2" in valid_choices:
                print("\n[OK] Selected: NVIDIA Riva TTS")
                return ("nvidia", NvidiaTTS())
            
            elif choice == "2":
                print("[X] NVIDIA TTS is not available. Please select option 1.")
            
            else:
                print("[X] Invalid choice. Please enter 1 or 2.")
                
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)


class VoiceAssistant:
    """
    Main voice assistant orchestrating all modules.
    
    Workflow:
    1. Listen for user speech
    2. Transcribe speech to text (STT)
    3. Generate AI response (LLM)
    4. Speak response (TTS) - interruptible
    5. Handle interrupts with context memory
    """
    
    def __init__(self, tts_provider: str = "groq", tts_instance = None):
        """
        Initialize all modules.
        
        Args:
            tts_provider: "groq" or "nvidia"
            tts_instance: Pre-initialized TTS instance
        """
        print("\nInitializing Voice Assistant...")
        
        # Validate config
        require_nvidia = (tts_provider == "nvidia")
        if not config.validate(require_nvidia=require_nvidia):
            sys.exit(1)
        
        # Initialize modules
        self.audio_input = AudioInput()
        
        # Use NVIDIA STT if available, otherwise fall back to Groq
        if NVIDIA_STT_AVAILABLE and config.NVIDIA_API_KEY:
            print("   STT: NVIDIA Whisper (whisper-large-v3)")
            self.stt = NvidiaSpeechToText()
        else:
            print("   STT: Groq Whisper")
            self.stt = SpeechToText()
        
        self.llm = LLMHandler()
        self.tts = tts_instance if tts_instance else TextToSpeech()
        self.interrupt_handler = InterruptHandler()
        
        # Track which TTS provider is in use
        self.tts_provider = tts_provider
        
        # State tracking  
        self.is_running = False
        self.current_response = ""
        self.current_question = ""
        
        # Set up callbacks
        self._setup_callbacks()
        
        print("[OK] Voice Assistant initialized!")
        print(f"   Model: {config.LLM_MODEL}")
        
        if tts_provider == "nvidia":
            print(f"   TTS: NVIDIA Riva ({config.NVIDIA_TTS_VOICE})")
        else:
            print(f"   TTS: Groq PlayAI ({config.TTS_VOICE})")
        print()
    
    def _setup_callbacks(self):
        """Set up callbacks between modules."""
        # Audio input callbacks
        self.audio_input.on_speech_start = self._on_user_speech_start
        self.audio_input.on_speech_end = self._on_user_speech_end
        
        # State change logging
        self.interrupt_handler.on_state_change = self._on_state_change
    
    def _on_state_change(self, old_state: AssistantState, new_state: AssistantState):
        """Handle state transitions."""
        if config.DEBUG:
            print(f"State: {old_state.name} -> {new_state.name}")
    
    def _on_user_speech_start(self):
        """Called when user starts speaking."""
        # If we're currently speaking, this is an interrupt!
        if self.tts.is_playing:
            self._handle_interrupt()
    
    def _on_user_speech_end(self, audio_data: bytes):
        """Called when user finishes speaking."""
        pass  # Handled in main loop
    
    def _handle_interrupt(self):
        """Handle user interrupting the assistant."""
        # Stop TTS immediately
        self.tts.stop()
        
        # Store context
        spoken = self.tts.get_spoken_portion()
        self.interrupt_handler.handle_interrupt(
            full_response=self.current_response,
            spoken_portion=spoken,
            user_question=self.current_question
        )
        
        # Store in LLM memory too
        self.llm.store_interrupted_context(
            partial_response=self.current_response,
            spoken_portion=spoken
        )
        
        print("\n[Interrupted]")
    
    def run(self):
        """Main run loop."""
        print("=" * 50)
        print("Voice Assistant Ready!")
        print("=" * 50)
        print("\nSpeak to start a conversation.")
        print("Say 'exit', 'quit', or 'goodbye' to stop.")
        print("Press Ctrl+C to force quit.\n")
        
        self.is_running = True
        self.interrupt_handler.set_state(AssistantState.LISTENING)
        
        # Start audio capture
        if not self.audio_input.start():
            print("[ERROR] Failed to start audio input!")
            return
        
        try:
            while self.is_running:
                self._process_loop()
                time.sleep(0.01)  # Small sleep to prevent CPU spinning
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        finally:
            self.shutdown()
    
    def _process_loop(self):
        """Main processing loop iteration."""
        state = self.interrupt_handler.state
        
        if state == AssistantState.LISTENING:
            self._handle_listening_state()
            
        elif state == AssistantState.INTERRUPTED:
            self._handle_interrupted_state()
            
        elif state == AssistantState.WAITING_RESUME:
            self._handle_waiting_resume_state()
    
    def _handle_listening_state(self):
        """Handle the LISTENING state - waiting for user input."""
        # Check for user speech
        audio_data = self.audio_input.get_speech(timeout=0.1)
        
        if audio_data:
            self._process_user_speech(audio_data)
    
    def _handle_interrupted_state(self):
        """Handle the INTERRUPTED state - user interrupted, waiting for their input or silence."""
        # Update speech activity
        self.interrupt_handler.update_speech_activity(self.audio_input.is_speaking)
        
        # Check if user is giving new input
        audio_data = self.audio_input.get_speech(timeout=0.1)
        
        if audio_data:
            # User spoke - process their new input
            self._process_user_speech(audio_data)
            
        elif self.interrupt_handler.should_prompt_resume():
            # User went silent after interrupting - ask what they wanted
            self._prompt_resume()
    
    def _handle_waiting_resume_state(self):
        """Handle waiting for user after resume prompt."""
        audio_data = self.audio_input.get_speech(timeout=0.1)
        
        if audio_data:
            # Transcribe what they said
            text = self.stt.transcribe(audio_data)
            
            if text:
                # Check if they want us to continue
                if self.interrupt_handler.should_offer_continuation(text):
                    continuation = self.interrupt_handler.get_continuation_text()
                    if continuation:
                        print(f"\nAssistant: {continuation}")
                        self._speak_response(continuation)
                    else:
                        # No continuation available, just process as new input
                        self._process_text_input(text)
                else:
                    # They have new input
                    self._process_text_input(text)
            
            self.interrupt_handler.set_state(AssistantState.LISTENING)
    
    def _process_user_speech(self, audio_data: bytes):
        """Process captured user speech."""
        self.interrupt_handler.set_state(AssistantState.PROCESSING)
        
        # Transcribe speech
        print("\nTranscribing...")
        start_time = time.time()
        
        text = self.stt.transcribe(audio_data)
        
        if not text:
            print("[ERROR] Could not transcribe audio")
            self.interrupt_handler.set_state(AssistantState.LISTENING)
            return
        
        stt_time = time.time() - start_time
        print(f"You: {text}")
        
        if config.DEBUG:
            print(f"   (STT: {stt_time:.2f}s)")
        
        self._process_text_input(text)
    
    def _process_text_input(self, text: str):
        """Process text input and generate response."""
        # Check for exit commands
        if self._is_exit_command(text):
            print("\nGoodbye! Have a great day!")
            self.tts.speak("Goodbye! Have a great day!", blocking=True)
            self.is_running = False
            return
        
        self.current_question = text
        
        # Generate LLM response
        print("Thinking...")
        start_time = time.time()
        
        response = self.llm.generate_response(text)
        
        llm_time = time.time() - start_time
        
        if config.DEBUG:
            print(f"   (LLM: {llm_time:.2f}s)")
        
        print(f"Assistant: {response}")
        
        self.current_response = response
        
        # Speak the response (interruptible)
        self._speak_response(response)
    
    def _speak_response(self, response: str):
        """Speak a response with interrupt monitoring."""
        self.interrupt_handler.set_state(AssistantState.SPEAKING)
        
        # Keep microphone active to detect interrupts
        # Note: Use headphones to avoid echo/self-triggering issues
        self.audio_input.muted = False
        
        # Start TTS in background
        self.tts.speak_chunked(response)
        
        # Monitor for interrupts while speaking
        while self.tts.is_playing:
            # Check if user is speaking (interrupt detected)
            if self.audio_input.is_speaking:
                self._handle_interrupt()
                break
            time.sleep(0.01)
        
        # Finished speaking (either completed or interrupted)
        if self.interrupt_handler.state == AssistantState.SPEAKING:
            # Only transition to LISTENING if we weren't interrupted
            self.interrupt_handler.set_state(AssistantState.LISTENING)
            self.interrupt_handler.clear_interrupt_context()
    
    def _prompt_resume(self):
        """Prompt user after they interrupted then went silent."""
        prompt = self.interrupt_handler.get_resume_response()
        print(f"\nAssistant: {prompt}")
        self.tts.speak(prompt, blocking=True)
    
    def _is_exit_command(self, text: str) -> bool:
        """Check if the user wants to exit."""
        text_lower = text.lower().strip()
        exit_phrases = [
            "exit", "quit", "goodbye", "bye", "stop",
            "shut down", "close", "end", "terminate",
            "i'm done", "that's all", "thanks bye"
        ]
        return any(phrase in text_lower for phrase in exit_phrases)
    
    def shutdown(self):
        """Clean up and shutdown."""
        print("\nShutting down...")
        self.is_running = False
        self.audio_input.stop()
        self.tts.cleanup()
        print("[OK] Shutdown complete")


def main():
    """Entry point."""
    # Check Python version
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8 or higher is required")
        sys.exit(1)
    
    # Show TTS selection menu
    tts_provider, tts_instance = select_tts_provider()

    # Set emotion for NVIDIA TTS (Groq doesn't support this)
    if tts_provider == "nvidia" and hasattr(tts_instance, 'set_emotion'):
        tts_instance.set_emotion('happy')  
    
    # Create and run assistant
    assistant = VoiceAssistant(tts_provider=tts_provider, tts_instance=tts_instance)
    assistant.run()


if __name__ == "__main__":
    main()
