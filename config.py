"""
Configuration settings for borgo-ai
Optimized for 16GB RAM + RTX 3060 Ti
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import json

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
USERS_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR.mkdir(exist_ok=True)


@dataclass
class LLMConfig:
    """
    LLM Configuration - optimized for RTX 3060 Ti (8GB VRAM)
    
    Available Models (use /model command to switch):
    ┌─────────────────────────────────┬────────┬─────────────────────────────────────┐
    │ Model                           │ VRAM   │ Best For                            │
    ├─────────────────────────────────┼────────┼─────────────────────────────────────┤
    │ wizard-vicuna-uncensored:13b    │ ~8GB   │ ⭐ TRULY UNCENSORED - no limits     │
    │ dolphin-mistral:7b-v2.6         │ ~5GB   │ Uncensored + great coder            │
    │ dolphin-llama3:8b               │ ~5GB   │ Good all-rounder                    │
    │ nous-hermes2:10.7b              │ ~7GB   │ 🧠 Complex tasks                    │
    │ deepseek-coder:6.7b             │ ~5GB   │ 💻 Specialized coding               │
    │ llava                           │ ~5GB   │ 👁️ Vision/image description        │
    └─────────────────────────────────┴────────┴─────────────────────────────────────┘
    """
    model: str = "dolphin-llama3:8b"  # Default: best all-rounder
    base_url: str = "http://localhost:11434"
    temperature: float = 0.8  # Slightly higher for more creative/natural responses
    max_tokens: int = 4096  # Longer responses
    context_window: int = 8192
    top_p: float = 0.9
    repeat_penalty: float = 1.05  # Lower to avoid repetitive refusals


@dataclass
class EmbeddingConfig:
    """Embedding Configuration"""
    model: str = "nomic-embed-text"  # Lightweight, runs well on 3060 Ti
    dimension: int = 768
    chunk_size: int = 512
    chunk_overlap: int = 50


@dataclass
class MemoryConfig:
    """Memory system configuration"""
    max_short_term_messages: int = 20  # Recent conversation context
    max_long_term_memories: int = 100  # Important memories to persist
    similarity_threshold: float = 0.7  # For memory retrieval
    auto_summarize_after: int = 10  # Auto-summarize after N messages


@dataclass 
class BrowserConfig:
    """Browser/Search configuration"""
    max_search_results: int = 5
    max_page_content_length: int = 4000  # Characters per page
    request_timeout: int = 10
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class AgentConfig:
    """Agentic mode configuration"""
    max_iterations: int = 10
    tools_enabled: list = field(default_factory=lambda: [
        "search_web",
        "read_url",
        "remember",
        "recall",
        "calculate",
        "get_time"
    ])


@dataclass
class UserSettings:
    """Per-user settings"""
    username: str = "default"
    theme: str = "cyber"  # cyber, minimal, retro
    show_thinking: bool = True
    auto_browse: bool = False  # Auto-search when AI thinks it's needed
    agentic_mode: bool = False
    markdown_enabled: bool = True
    stream_output: bool = True
    memory_enabled: bool = True
    
    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "theme": self.theme,
            "show_thinking": self.show_thinking,
            "auto_browse": self.auto_browse,
            "agentic_mode": self.agentic_mode,
            "markdown_enabled": self.markdown_enabled,
            "stream_output": self.stream_output,
            "memory_enabled": self.memory_enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        return cls(**data)
    
    def save(self):
        user_dir = USERS_DIR / self.username
        user_dir.mkdir(exist_ok=True)
        settings_file = user_dir / "settings.json"
        with open(settings_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, username: str) -> "UserSettings":
        settings_file = USERS_DIR / username / "settings.json"
        if settings_file.exists():
            with open(settings_file) as f:
                return cls.from_dict(json.load(f))
        return cls(username=username)


# Global config instances
llm_config = LLMConfig()
embedding_config = EmbeddingConfig()
memory_config = MemoryConfig()
browser_config = BrowserConfig()
agent_config = AgentConfig()
