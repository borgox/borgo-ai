"""
Summarizer Module - Conversation and text summarization for borgo-ai
Helps manage context window by summarizing old conversations
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

from .llm import get_llm, Message


@dataclass
class Summary:
    """A summary of content"""
    original_length: int
    summary_length: int
    summary: str
    key_points: List[str]
    compression_ratio: float


class Summarizer:
    """
    Summarize conversations and text to manage context.
    
    Why summarization matters:
    - LLMs have limited context windows (8k-128k tokens)
    - Old messages eat up context space
    - Summaries preserve important info in less space
    - Better responses when relevant context fits
    """
    
    def __init__(self):
        self.llm = get_llm()
    
    def summarize_text(self, text: str, max_length: int = 500) -> Summary:
        """Summarize arbitrary text"""
        prompt = f"""Summarize the following text concisely. Keep the most important information.
Maximum summary length: {max_length} characters.

Text to summarize:
{text}

Provide:
1. A concise summary
2. 3-5 key bullet points

Format your response as:
SUMMARY: <your summary here>

KEY POINTS:
• <point 1>
• <point 2>
• <point 3>
"""
        
        response = self.llm.generate(prompt, stream=False)
        
        # Parse response
        summary = ""
        key_points = []
        
        if "SUMMARY:" in response:
            parts = response.split("KEY POINTS:")
            summary = parts[0].replace("SUMMARY:", "").strip()
            
            if len(parts) > 1:
                points_text = parts[1].strip()
                for line in points_text.split('\n'):
                    line = line.strip()
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        key_points.append(line[1:].strip())
        else:
            summary = response.strip()
        
        return Summary(
            original_length=len(text),
            summary_length=len(summary),
            summary=summary,
            key_points=key_points,
            compression_ratio=len(summary) / len(text) if text else 0
        )
    
    def summarize_conversation(
        self, 
        messages: List[Dict[str, str]],
        preserve_last: int = 4
    ) -> Dict:
        """
        Summarize a conversation, preserving recent messages.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            preserve_last: Number of recent messages to keep intact
        
        Returns:
            Dict with 'summary' and 'preserved_messages'
        """
        if len(messages) <= preserve_last:
            return {
                "summary": None,
                "preserved_messages": messages,
                "summarized_count": 0
            }
        
        # Split messages
        to_summarize = messages[:-preserve_last]
        to_preserve = messages[-preserve_last:]
        
        # Format conversation for summarization
        conv_text = ""
        for msg in to_summarize:
            role = "User" if msg["role"] == "user" else "Assistant"
            conv_text += f"{role}: {msg['content']}\n\n"
        
        prompt = f"""Summarize this conversation. Capture:
- Main topics discussed
- Key decisions or conclusions
- Important facts mentioned
- Any tasks or action items

Conversation:
{conv_text}

Write a concise summary (2-3 paragraphs) that captures the essential information:"""
        
        summary = self.llm.generate(prompt, stream=False)
        
        return {
            "summary": summary.strip(),
            "preserved_messages": to_preserve,
            "summarized_count": len(to_summarize)
        }
    
    def create_memory_from_conversation(
        self, 
        messages: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract important facts from a conversation to save as memories.
        
        Returns a list of fact strings.
        """
        conv_text = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            conv_text += f"{role}: {msg['content']}\n\n"
        
        prompt = f"""Analyze this conversation and extract important facts that should be remembered for future conversations.

Focus on:
- Personal information the user shared (name, preferences, etc.)
- Important decisions or conclusions
- Specific facts or data mentioned
- User preferences or requirements

Conversation:
{conv_text}

List each important fact on its own line, prefixed with "FACT:". Only include genuinely important information worth remembering. If nothing important, respond with "NO_FACTS".

Facts:"""
        
        response = self.llm.generate(prompt, stream=False)
        
        if "NO_FACTS" in response:
            return []
        
        facts = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith("FACT:"):
                fact = line[5:].strip()
                if fact:
                    facts.append(fact)
        
        return facts
    
    def summarize_for_context(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000
    ) -> str:
        """
        Create a context-optimized summary for injecting into prompts.
        
        This is useful when you want to include conversation history
        but need to fit within token limits.
        """
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        # If messages fit, just format them
        formatted = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "AI"
            formatted += f"{role}: {msg['content']}\n"
        
        if len(formatted) <= max_chars:
            return formatted
        
        # Need to summarize
        result = self.summarize_conversation(messages, preserve_last=2)
        
        output = f"[Previous conversation summary]\n{result['summary']}\n\n[Recent messages]\n"
        for msg in result['preserved_messages']:
            role = "User" if msg["role"] == "user" else "AI"
            output += f"{role}: {msg['content']}\n"
        
        return output


class ConversationCompressor:
    """
    Automatically compress conversation history when it gets too long.
    
    Strategy:
    1. Keep last N messages intact
    2. Summarize older messages
    3. Extract and save important facts as memories
    """
    
    def __init__(
        self,
        max_messages: int = 20,
        summarize_after: int = 10,
        preserve_recent: int = 4
    ):
        self.max_messages = max_messages
        self.summarize_after = summarize_after
        self.preserve_recent = preserve_recent
        self.summarizer = Summarizer()
        self.conversation_summary: Optional[str] = None
    
    def should_compress(self, message_count: int) -> bool:
        """Check if we should compress"""
        return message_count > self.summarize_after
    
    def compress(
        self, 
        messages: List[Dict[str, str]]
    ) -> tuple:
        """
        Compress conversation.
        
        Returns:
            (compressed_messages, summary, extracted_facts)
        """
        if not self.should_compress(len(messages)):
            return messages, None, []
        
        # Summarize
        result = self.summarizer.summarize_conversation(
            messages, 
            preserve_last=self.preserve_recent
        )
        
        # Extract facts
        to_summarize = messages[:-self.preserve_recent]
        facts = self.summarizer.create_memory_from_conversation(to_summarize)
        
        # Store summary
        self.conversation_summary = result["summary"]
        
        return result["preserved_messages"], result["summary"], facts
    
    def get_context_with_summary(
        self, 
        recent_messages: List[Dict[str, str]]
    ) -> str:
        """Get formatted context including summary"""
        context = ""
        
        if self.conversation_summary:
            context += f"[Earlier in this conversation]\n{self.conversation_summary}\n\n"
        
        context += "[Recent messages]\n"
        for msg in recent_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"
        
        return context


# Convenience functions
_summarizer: Optional[Summarizer] = None

def get_summarizer() -> Summarizer:
    """Get or create summarizer"""
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer


def summarize_text(text: str, max_length: int = 500) -> Summary:
    """Summarize text"""
    return get_summarizer().summarize_text(text, max_length)


def summarize_conversation(
    messages: List[Dict[str, str]], 
    preserve_last: int = 4
) -> Dict:
    """Summarize a conversation"""
    return get_summarizer().summarize_conversation(messages, preserve_last)


def extract_facts(messages: List[Dict[str, str]]) -> List[str]:
    """Extract facts from conversation"""
    return get_summarizer().create_memory_from_conversation(messages)
