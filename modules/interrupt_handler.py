"""
Interrupt Handler Module - Manages conversation state and interrupt detection.
Implements a state machine for smooth conversation flow with interrupt handling.
"""

import time
import random
from enum import Enum, auto
from typing import Optional, Callable
from dataclasses import dataclass, field

import sys
sys.path.append('..')
from config import config


class AssistantState(Enum):
    """States of the voice assistant."""
    IDLE = auto()           # Not doing anything
    LISTENING = auto()      # Waiting for user speech
    PROCESSING = auto()     # Processing user input (STT + LLM)
    SPEAKING = auto()       # Playing TTS response
    INTERRUPTED = auto()    # User interrupted, waiting for input or silence
    WAITING_RESUME = auto() # Asked user to continue, waiting for response


@dataclass
class InterruptContext:
    """Context information when an interrupt occurs."""
    full_response: str = ""
    spoken_portion: str = ""
    remaining_text: str = ""
    user_question: str = ""
    timestamp: float = field(default_factory=time.time)
    

class InterruptHandler:
    """
    Handles conversation interrupts and state transitions.
    
    Features:
    - State machine for conversation flow
    - Interrupt detection during TTS playback
    - Context preservation for interrupted responses
    - Natural resume prompt generation
    """
    
    def __init__(self):
        """Initialize the interrupt handler."""
        self.state = AssistantState.IDLE
        self.previous_state = AssistantState.IDLE
        
        # Interrupt context
        self.interrupt_context: Optional[InterruptContext] = None
        self.interrupt_count = 0
        
        # Timing
        self.state_start_time = time.time()
        self.last_speech_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        
        # Callbacks for state changes
        self.on_state_change: Optional[Callable[[AssistantState, AssistantState], None]] = None
        
        # Silence threshold for triggering resume prompt
        self.resume_silence_threshold_ms = 1500  # 1.5 seconds of silence
        
    def set_state(self, new_state: AssistantState):
        """
        Transition to a new state.
        
        Args:
            new_state: The new state to transition to
        """
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            self.state_start_time = time.time()
            
            if config.DEBUG:
                print(f"[STATE] {self.previous_state.name} -> {new_state.name}")
            
            if self.on_state_change:
                self.on_state_change(self.previous_state, new_state)
    
    def handle_interrupt(self, full_response: str, spoken_portion: str, user_question: str):
        """
        Handle an interrupt event - user spoke while assistant was speaking.
        
        Args:
            full_response: The complete response that was being spoken
            spoken_portion: The part that was actually spoken
            user_question: The original question that prompted this response
        """
        remaining = full_response[len(spoken_portion):].strip()
        
        self.interrupt_context = InterruptContext(
            full_response=full_response,
            spoken_portion=spoken_portion,
            remaining_text=remaining,
            user_question=user_question,
            timestamp=time.time()
        )
        
        self.interrupt_count += 1
        self.set_state(AssistantState.INTERRUPTED)
        self.silence_start_time = None
        
        if config.DEBUG:
            print(f"[INTERRUPT] Detected! Spoken: {len(spoken_portion)} chars, Remaining: {len(remaining)} chars")
    
    def update_speech_activity(self, is_speaking: bool):
        """
        Update based on user speech activity.
        Called continuously during INTERRUPTED state.
        
        Args:
            is_speaking: Whether the user is currently speaking
        """
        current_time = time.time()
        
        if is_speaking:
            self.last_speech_time = current_time
            self.silence_start_time = None
        else:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
    
    def should_prompt_resume(self) -> bool:
        """
        Check if we should prompt the user to continue.
        Called when user interrupted then went silent.
        
        Returns:
            True if we should ask user to continue
        """
        if self.state != AssistantState.INTERRUPTED:
            return False
            
        if self.silence_start_time is None:
            return False
            
        silence_duration_ms = (time.time() - self.silence_start_time) * 1000
        
        return silence_duration_ms >= self.resume_silence_threshold_ms
    
    def get_resume_response(self) -> str:
        """
        Get a natural response when user interrupted then went silent.
        
        Returns:
            A human-like prompt asking user to continue
        """
        # Choose from various natural responses
        responses = [
            "Yes? I'm listening.",
            "Go ahead, I'm all ears.",
            "Sorry, what were you going to say?",
            "Yes, please continue.",
            "I'm listening, go ahead.",
            "What's on your mind?",
            "You have my attention.",
        ]
        
        # If they've interrupted multiple times, be more accommodating
        if self.interrupt_count > 2:
            responses.extend([
                "No worries, take your time. What would you like to say?",
                "I'm here. Please, go ahead.",
            ])
        
        self.set_state(AssistantState.WAITING_RESUME)
        return random.choice(responses)
    
    def has_interrupted_context(self) -> bool:
        """
        Check if there's interrupted context that can be resumed.
        
        Returns:
            True if there's context to resume
        """
        return (
            self.interrupt_context is not None and 
            len(self.interrupt_context.remaining_text) > 0
        )
    
    def should_offer_continuation(self, user_response: str) -> bool:
        """
        Check if we should offer to continue the interrupted response.
        Based on user's response after we asked them to continue.
        
        Args:
            user_response: What the user said
            
        Returns:
            True if user seems to want us to continue
        """
        user_response = user_response.lower().strip()
        
        # Keywords that suggest they want us to continue
        continue_keywords = [
            "continue", "go on", "go ahead", "carry on",
            "keep going", "yes", "yeah", "yep", "sure",
            "please", "ok", "okay", "never mind", "nevermind",
            "nothing", "sorry", "my bad", "oops"
        ]
        
        for keyword in continue_keywords:
            if keyword in user_response:
                return True
        
        # Short responses might indicate they want us to continue
        if len(user_response.split()) <= 3:
            return True
            
        return False
    
    def get_continuation_text(self) -> Optional[str]:
        """
        Get the remaining text from interrupted response.
        
        Returns:
            Remaining text or None
        """
        if self.interrupt_context and self.interrupt_context.remaining_text:
            # Add a brief connector
            connectors = ["As I was saying, ", "So, ", "Anyway, ", ""]
            remaining = self.interrupt_context.remaining_text
            self.clear_interrupt_context()
            return random.choice(connectors) + remaining
        return None
    
    def clear_interrupt_context(self):
        """Clear the stored interrupt context."""
        self.interrupt_context = None
    
    def reset(self):
        """Reset all state to initial values."""
        self.state = AssistantState.IDLE
        self.previous_state = AssistantState.IDLE
        self.interrupt_context = None
        self.interrupt_count = 0
        self.silence_start_time = None
        self.last_speech_time = None
        
        if config.DEBUG:
            print("[RESET] Interrupt handler reset")
    
    def get_state_duration(self) -> float:
        """
        Get how long we've been in the current state.
        
        Returns:
            Duration in seconds
        """
        return time.time() - self.state_start_time
    
    def is_active_conversation(self) -> bool:
        """
        Check if we're in an active conversation state.
        
        Returns:
            True if in conversation
        """
        return self.state not in [AssistantState.IDLE]
    
    def get_status_display(self) -> str:
        """
        Get a display string for current status.
        Useful for UI feedback.
        
        Returns:
            Status string
        """
        status_map = {
            AssistantState.IDLE: "[IDLE] Ready",
            AssistantState.LISTENING: "[LISTENING] Listening...",
            AssistantState.PROCESSING: "[PROCESSING] Thinking...",  
            AssistantState.SPEAKING: "[SPEAKING] Speaking...",
            AssistantState.INTERRUPTED: "[PAUSED] Interrupted",
            AssistantState.WAITING_RESUME: "[WAITING] Waiting for you...",
        }
        return status_map.get(self.state, "[?] Unknown")
