"""
User Module - User management and settings for borgo-ai
"""
import json
import shutil
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from config import USERS_DIR, UserSettings
from memory import MemoryManager, get_memory_manager


class UserManager:
    """Manages users and their settings"""
    
    def __init__(self):
        self.users_dir = USERS_DIR
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.current_user: Optional[str] = None
        self.current_settings: Optional[UserSettings] = None
        self._load_last_user()
    
    def _load_last_user(self):
        """Load the last active user"""
        state_file = self.users_dir / ".state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                last_user = state.get("last_user", "default")
                if self.user_exists(last_user):
                    self.switch_user(last_user)
                    return
        
        # Default to "default" user
        if not self.user_exists("default"):
            self.create_user("default")
        self.switch_user("default")
    
    def _save_state(self):
        """Save current state"""
        state_file = self.users_dir / ".state.json"
        with open(state_file, "w") as f:
            json.dump({
                "last_user": self.current_user
            }, f)
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists"""
        user_dir = self.users_dir / username
        return user_dir.exists() and (user_dir / "settings.json").exists()
    
    def list_users(self) -> List[str]:
        """List all users"""
        users = []
        for item in self.users_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                if (item / "settings.json").exists():
                    users.append(item.name)
        return sorted(users)
    
    def create_user(self, username: str) -> bool:
        """Create a new user"""
        if self.user_exists(username):
            return False
        
        # Create user directory
        user_dir = self.users_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default settings
        settings = UserSettings(username=username)
        settings.save()
        
        return True
    
    def delete_user(self, username: str) -> bool:
        """Delete a user and all their data"""
        if username == "default":
            return False  # Don't delete default user
        
        if not self.user_exists(username):
            return False
        
        user_dir = self.users_dir / username
        shutil.rmtree(user_dir)
        
        if self.current_user == username:
            self.switch_user("default")
        
        return True
    
    def switch_user(self, username: str) -> bool:
        """Switch to a different user"""
        if not self.user_exists(username):
            if not self.create_user(username):
                return False
        
        self.current_user = username
        self.current_settings = UserSettings.load(username)
        self._save_state()
        
        return True
    
    def get_settings(self) -> UserSettings:
        """Get current user settings"""
        if not self.current_settings:
            self.current_settings = UserSettings.load(self.current_user or "default")
        return self.current_settings
    
    def update_settings(self, **kwargs) -> UserSettings:
        """Update current user settings"""
        settings = self.get_settings()
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.save()
        self.current_settings = settings
        return settings
    
    def get_memory_manager(self) -> MemoryManager:
        """Get memory manager for current user"""
        return get_memory_manager(self.current_user or "default")
    
    def get_user_stats(self, username: str = None) -> Dict:
        """Get statistics for a user"""
        username = username or self.current_user or "default"
        
        if not self.user_exists(username):
            return {}
        
        user_dir = self.users_dir / username
        
        # Count conversations
        convs_file = user_dir / "conversations.json"
        num_conversations = 0
        num_messages = 0
        if convs_file.exists():
            with open(convs_file) as f:
                data = json.load(f)
                convs = data.get("conversations", [])
                num_conversations = len(convs)
                for conv in convs:
                    num_messages += len(conv.get("messages", []))
        
        # Count memories
        mems_file = user_dir / "memories.json"
        num_memories = 0
        if mems_file.exists():
            with open(mems_file) as f:
                data = json.load(f)
                num_memories = len(data.get("memories", []))
        
        # Get directory size
        total_size = sum(f.stat().st_size for f in user_dir.rglob("*") if f.is_file())
        
        return {
            "username": username,
            "conversations": num_conversations,
            "messages": num_messages,
            "memories": num_memories,
            "storage_bytes": total_size,
            "storage_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def wipe_user_data(self, username: str = None, wipe_settings: bool = False):
        """Wipe all data for a user"""
        username = username or self.current_user or "default"
        
        if not self.user_exists(username):
            return
        
        mm = get_memory_manager(username)
        mm.wipe_all()
        
        if wipe_settings:
            # Reset to default settings
            settings = UserSettings(username=username)
            settings.save()
            if username == self.current_user:
                self.current_settings = settings
    
    def export_user_data(self, username: str = None) -> Dict:
        """Export all user data"""
        username = username or self.current_user or "default"
        
        mm = get_memory_manager(username)
        settings = UserSettings.load(username)
        
        return {
            "username": username,
            "settings": settings.to_dict(),
            "memory_data": mm.export_data(),
            "stats": self.get_user_stats(username)
        }


# Singleton instance
_user_manager: Optional[UserManager] = None

def get_user_manager() -> UserManager:
    """Get or create user manager"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


def get_current_user() -> str:
    """Get current username"""
    return get_user_manager().current_user or "default"


def get_current_settings() -> UserSettings:
    """Get current user settings"""
    return get_user_manager().get_settings()
