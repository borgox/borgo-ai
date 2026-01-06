"""
Memory Module - Conversation memory and persistence for borgo-ai
"""
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import uuid

from config import USERS_DIR, memory_config
from embeddings import FAISSIndex, get_embedder, embed_text, embedding_config


@dataclass
class ChatMessage:
    """Individual chat message"""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(**data)


@dataclass
class Conversation:
    """A conversation session"""
    conversation_id: str
    title: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append(ChatMessage(role=role, content=content))
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            conversation_id=data["conversation_id"],
            title=data["title"],
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


@dataclass
class Memory:
    """A long-term memory entry"""
    memory_id: str
    content: str
    importance: float  # 0-1, higher is more important
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "conversation"  # conversation, user, system
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(**data)


class MemoryManager:
    """Manages conversation history and long-term memory"""
    
    def __init__(self, username: str = "default"):
        self.username = username
        self.user_dir = USERS_DIR / username
        self.user_dir.mkdir(parents=True, exist_ok=True)
        
        self.conversations_file = self.user_dir / "conversations.json"
        self.memories_file = self.user_dir / "memories.json"
        self.memory_index_dir = self.user_dir / "memory_index"
        
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation: Optional[Conversation] = None
        self.memories: List[Memory] = []
        self.memory_index: Optional[FAISSIndex] = None
        
        self._load_data()
    
    def _load_data(self):
        """Load all saved data"""
        # Load conversations
        if self.conversations_file.exists():
            with open(self.conversations_file) as f:
                data = json.load(f)
                for conv_data in data.get("conversations", []):
                    conv = Conversation.from_dict(conv_data)
                    self.conversations[conv.conversation_id] = conv
        
        # Load memories
        if self.memories_file.exists():
            with open(self.memories_file) as f:
                data = json.load(f)
                self.memories = [Memory.from_dict(m) for m in data.get("memories", [])]
        
        # Load memory index
        if (self.memory_index_dir / "index.faiss").exists():
            try:
                self.memory_index = FAISSIndex.load(self.memory_index_dir)
            except:
                self._rebuild_memory_index()
        else:
            self._rebuild_memory_index()
    
    def _save_conversations(self):
        """Save conversations to disk"""
        data = {
            "conversations": [c.to_dict() for c in self.conversations.values()]
        }
        with open(self.conversations_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _save_memories(self):
        """Save memories to disk"""
        data = {
            "memories": [m.to_dict() for m in self.memories]
        }
        with open(self.memories_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _rebuild_memory_index(self):
        """Rebuild the memory vector index"""
        self.memory_index = FAISSIndex(dimension=embedding_config.dimension)
        
        if not self.memories:
            return
        
        embedder = get_embedder()
        contents = [m.content for m in self.memories]
        
        if contents:
            embeddings = embedder.embed_batch(contents)
            metadata = [m.to_dict() for m in self.memories]
            self.memory_index.add(embeddings, contents, metadata)
            self.memory_index.save(self.memory_index_dir)
    
    # Conversation Management
    
    def new_conversation(self, title: str = None) -> Conversation:
        """Start a new conversation"""
        conv_id = str(uuid.uuid4())[:8]
        title = title or f"Chat {len(self.conversations) + 1}"
        
        conv = Conversation(conversation_id=conv_id, title=title)
        self.conversations[conv_id] = conv
        self.current_conversation = conv
        self._save_conversations()
        
        return conv
    
    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get a specific conversation"""
        return self.conversations.get(conv_id)
    
    def load_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Load and set as current conversation"""
        conv = self.get_conversation(conv_id)
        if conv:
            self.current_conversation = conv
        return conv
    
    def list_conversations(self) -> List[Dict]:
        """List all conversations"""
        convs = sorted(
            self.conversations.values(),
            key=lambda x: x.updated_at,
            reverse=True
        )
        return [{
            "id": c.conversation_id,
            "title": c.title,
            "messages": len(c.messages),
            "updated": c.updated_at
        } for c in convs]
    
    def delete_conversation(self, conv_id: str):
        """Delete a conversation"""
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            if self.current_conversation and self.current_conversation.conversation_id == conv_id:
                self.current_conversation = None
            self._save_conversations()
    
    def add_message(self, role: str, content: str):
        """Add message to current conversation"""
        if not self.current_conversation:
            self.new_conversation()
        
        self.current_conversation.add_message(role, content)
        self._save_conversations()
        
        # Auto-generate title from first user message
        if len(self.current_conversation.messages) == 1 and role == "user":
            self.current_conversation.title = content[:50] + ("..." if len(content) > 50 else "")
            self._save_conversations()
    
    def get_recent_messages(self, n: int = None) -> List[Dict]:
        """Get recent messages from current conversation"""
        if not self.current_conversation:
            return []
        
        n = n or memory_config.max_short_term_messages
        messages = self.current_conversation.messages[-n:]
        return [{"role": m.role, "content": m.content} for m in messages]
    
    # Long-term Memory Management
    
    def add_memory(
        self, 
        content: str, 
        importance: float = 0.5,
        source: str = "conversation",
        tags: List[str] = None
    ):
        """Add a long-term memory"""
        memory = Memory(
            memory_id=str(uuid.uuid4())[:8],
            content=content,
            importance=importance,
            source=source,
            tags=tags or []
        )
        
        self.memories.append(memory)
        
        # Add to index
        if self.memory_index is None:
            self._rebuild_memory_index()
        else:
            embedder = get_embedder()
            embedding = embedder.embed_text(content).reshape(1, -1)
            self.memory_index.add(embedding, [content], [memory.to_dict()])
            self.memory_index.save(self.memory_index_dir)
        
        # Trim if too many memories
        if len(self.memories) > memory_config.max_long_term_memories:
            # Remove least important memories
            self.memories.sort(key=lambda x: x.importance, reverse=True)
            self.memories = self.memories[:memory_config.max_long_term_memories]
            self._rebuild_memory_index()
        
        self._save_memories()
    
    def recall_memories(
        self, 
        query: str, 
        k: int = 5,
        min_score: float = None
    ) -> List[Dict]:
        """Recall relevant memories"""
        if not self.memory_index or len(self.memory_index) == 0:
            return []
        
        min_score = min_score or memory_config.similarity_threshold
        
        query_embedding = embed_text(query)
        results = self.memory_index.search(query_embedding, k)
        
        recalled = []
        for content, score, metadata in results:
            if score >= min_score:
                recalled.append({
                    "content": content,
                    "score": score,
                    "importance": metadata.get("importance", 0.5),
                    "timestamp": metadata.get("timestamp", ""),
                    "source": metadata.get("source", "unknown")
                })
        
        return recalled
    
    def list_memories(self) -> List[Dict]:
        """List all memories"""
        return [m.to_dict() for m in sorted(
            self.memories,
            key=lambda x: x.timestamp,
            reverse=True
        )]
    
    def delete_memory(self, memory_id: str):
        """Delete a specific memory"""
        self.memories = [m for m in self.memories if m.memory_id != memory_id]
        self._rebuild_memory_index()
        self._save_memories()
    
    # Data Management
    
    def wipe_conversations(self):
        """Delete all conversations"""
        self.conversations = {}
        self.current_conversation = None
        self._save_conversations()
    
    def wipe_memories(self):
        """Delete all memories"""
        self.memories = []
        self.memory_index = FAISSIndex(dimension=embedding_config.dimension)
        self._save_memories()
        self.memory_index.save(self.memory_index_dir)
    
    def wipe_all(self):
        """Wipe all user data"""
        self.wipe_conversations()
        self.wipe_memories()
    
    def export_data(self) -> Dict:
        """Export all user data"""
        return {
            "username": self.username,
            "conversations": [c.to_dict() for c in self.conversations.values()],
            "memories": [m.to_dict() for m in self.memories],
            "exported_at": datetime.now().isoformat()
        }
    
    def get_context_for_prompt(self, query: str) -> str:
        """Get relevant context from memory for a query"""
        context_parts = []
        
        # Get relevant memories
        memories = self.recall_memories(query, k=3)
        if memories:
            context_parts.append("### Relevant Memories:")
            for mem in memories:
                context_parts.append(f"- {mem['content']}")
        
        return "\n".join(context_parts)


# Convenience functions
_memory_managers: Dict[str, MemoryManager] = {}

def get_memory_manager(username: str = "default") -> MemoryManager:
    """Get or create memory manager for user"""
    if username not in _memory_managers:
        _memory_managers[username] = MemoryManager(username)
    return _memory_managers[username]
