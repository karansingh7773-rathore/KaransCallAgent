"""
LLM Handler Module - Manages conversation with Groq's LLM.
Handles conversation history, streaming responses, and interrupt memory.
"""

import random
from typing import Optional, Generator, List, Dict
from groq import Groq

import sys
sys.path.append('..')
from config import config


class LLMHandler:
    """
    Handles LLM interactions with conversation history and interrupt memory.
    
    Features:
    - Conversation history management
    - Streaming response support
    - Interrupt context storage
    - Resume prompt generation
    - Web search integration for real-time information
    """
    
    def __init__(self):
        """Initialize the LLM handler with Groq client."""
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.LLM_MODEL
        
        # Conversation history
        self.history: List[Dict[str, str]] = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]
        
        # Interrupt memory
        self.interrupted_response: Optional[str] = None
        self.was_interrupted = False
        
        # Max history to keep (to prevent token overflow)
        self.max_history_messages = 20
        
        self.web_search = None
        self._init_web_search()
        
    def update_system_prompt(self, prompt: str):
        """
        Update the system prompt (first message in history).
        
        Args:
            prompt: New system prompt
        """
        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = prompt
            if config.DEBUG:
                print(f"[DEBUG] System prompt updated")
        else:
            # Should not happen given __init__, but safe fallback
            self.history.insert(0, {"role": "system", "content": prompt})

    def add_user_message(self, message: str):
        """
        Add a user message to conversation history.
        
        Args:
            message: User's message text
        """
        self.history.append({
            "role": "user",
            "content": message
        })
        self._trim_history()
        
    def add_assistant_message(self, message: str):
        """
        Add an assistant message to conversation history.
        
        Args:
            message: Assistant's response text
        """
        self.history.append({
            "role": "assistant",
            "content": message
        })
        self._trim_history()
        
    def _trim_history(self):
        """Trim history to prevent token overflow, keeping system prompt."""
        if len(self.history) > self.max_history_messages + 1:  # +1 for system prompt
            # Keep system prompt and most recent messages
            self.history = [self.history[0]] + self.history[-(self.max_history_messages):]
    
    def _init_web_search(self):
        """Initialize web search handler (lazy import)."""
        try:
            from .web_search import WebSearchHandler
            self.web_search = WebSearchHandler()
            if self.web_search.enabled and config.DEBUG:
                print("[OK] Web search integration enabled")
        except Exception as e:
            if config.DEBUG:
                print(f"[WARN] Web search not available: {e}")
            self.web_search = None
    
    def _get_messages_with_search(self, user_input: str) -> List[Dict[str, str]]:
        """
        Get messages for LLM, optionally including web search results.
        Uses fast keyword detection - minimal latency impact.
        
        Args:
            user_input: User's message
            
        Returns:
            List of messages for LLM, potentially with search context
        """
        messages = self.history.copy()
        
        # Check if web search would help (fast keyword check)
        if self.web_search and self.web_search.enabled:
            search_context = self.web_search.get_search_context(user_input)
            
            if search_context:
                # Inject search results as a system message before the user query
                search_instruction = {
                    "role": "system",
                    "content": f"""Use the following web search results to inform your response. 
Cite the information naturally without mentioning you searched the web.
Keep your response concise for voice.

{search_context}"""
                }
                # Insert before the last user message
                messages.insert(-1, search_instruction)
                
                if config.DEBUG:
                    print(f"[DEBUG] Injected web search context")
        
        return messages
    
    def generate_response(self, user_input: str) -> str:
        """
        Generate a complete response for user input.
        Automatically fetches web search results for queries that need current info.
        
        Args:
            user_input: User's message
            
        Returns:
            Complete response text
        """
        # Add user message to history
        self.add_user_message(user_input)
        
        try:
            # Get messages with potential web search context
            messages = self._get_messages_with_search(user_input)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=500,  # Keep responses concise for voice
                top_p=0.9,
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add to history
            self.add_assistant_message(assistant_message)
            
            if config.DEBUG:
                print(f"[DEBUG] Response: {assistant_message}")
            
            return assistant_message
            
        except Exception as e:
            error_msg = f"I'm sorry, I encountered an error: {str(e)}"
            print(f"[ERROR] LLM error: {e}")
            return error_msg
    
    def generate_response_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        Generate a streaming response for user input.
        Yields chunks of text as they're generated.
        
        Args:
            user_input: User's message
            
        Yields:
            Text chunks as they're generated
        """
        # Add user message to history
        self.add_user_message(user_input)
        
        full_response = ""
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.7,
                max_completion_tokens=500,
                top_p=0.9,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_response += text_chunk
                    yield text_chunk
            
            # Add complete response to history
            if full_response:
                self.add_assistant_message(full_response)
                
            if config.DEBUG:
                print(f"[DEBUG] Streamed response: {full_response}")
                
        except Exception as e:
            error_msg = f"I'm sorry, I encountered an error."
            print(f"[ERROR] LLM streaming error: {e}")
            yield error_msg
    
    def store_interrupted_context(self, partial_response: str, spoken_portion: str = ""):
        """
        Store context when conversation is interrupted.
        
        Args:
            partial_response: The full response that was being generated
            spoken_portion: The portion that was actually spoken before interrupt
        """
        self.interrupted_response = partial_response
        self.was_interrupted = True
        
        if config.DEBUG:
            print(f"[DEBUG] Stored interrupted context: {partial_response[:50]}...")
    
    def get_resume_prompt(self) -> str:
        """
        Get a human-like prompt to resume after interrupt.
        
        Returns:
            A natural resume prompt
        """
        return random.choice(config.RESUME_PROMPTS)
    
    def should_resume_previous(self) -> bool:
        """
        Check if we should offer to resume a previous interrupted response.
        
        Returns:
            True if there's interrupted context to resume
        """
        return self.was_interrupted and self.interrupted_response is not None
    
    def get_continuation_response(self) -> str:
        """
        Get response offering to continue interrupted speech.
        
        Returns:
            A natural continuation offer
        """
        prompt = self.get_resume_prompt()
        self.was_interrupted = False  # Reset flag
        return prompt
    
    def handle_user_wants_continuation(self) -> Optional[str]:
        """
        If user wants us to continue, return the remaining response.
        
        Returns:
            Remaining response text or None
        """
        if self.interrupted_response:
            response = self.interrupted_response
            self.interrupted_response = None
            return response
        return None
    
    def clear_interrupt_context(self):
        """Clear the interrupted context."""
        self.interrupted_response = None
        self.was_interrupted = False
    
    def clear_history(self):
        """Clear conversation history, keeping only system prompt."""
        self.history = [self.history[0]]
        self.clear_interrupt_context()
        
        if config.DEBUG:
            print("[OK] Conversation history cleared")
    
    def get_history_summary(self) -> str:
        """
        Get a summary of conversation history for debugging.
        
        Returns:
            String summary of conversation
        """
        return f"Conversation has {len(self.history) - 1} messages (excluding system prompt)"


class LLMHandlerAsync:
    """
    Async version of LLM Handler for non-blocking operations.
    """
    
    def __init__(self):
        """Initialize async LLM handler."""
        from groq import AsyncGroq
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        self.model = config.LLM_MODEL
        self.history: List[Dict[str, str]] = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]
        self.max_history_messages = 20
        
    async def generate_response(self, user_input: str) -> str:
        """Generate response asynchronously."""
        self.history.append({"role": "user", "content": user_input})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.7,
                max_completion_tokens=500,
                top_p=0.9,
            )
            
            assistant_message = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            print(f"[ERROR] Async LLM error: {e}")
            return "I'm sorry, I encountered an error."
