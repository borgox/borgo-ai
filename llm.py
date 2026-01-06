"""
LLM Module - Ollama Integration for borgo-ai
Optimized for local inference on RTX 3060 Ti
"""
import requests
import json
from typing import Generator, Optional, List, Dict, Any
from dataclasses import dataclass
from config import llm_config


@dataclass
class Message:
    """Chat message structure"""
    role: str  # "system", "user", "assistant"
    content: str
    
    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class OllamaLLM:
    """Ollama LLM client for local inference"""
    
    def __init__(self, config=None):
        self.config = config or llm_config
        self.base_url = self.config.base_url
        self.model = self.config.model
        
    def _make_request(self, endpoint: str, data: dict, stream: bool = False):
        """Make request to Ollama API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(
                url,
                json=data,
                stream=stream,
                timeout=120
            )
            response.raise_for_status()
            return response
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"❌ Cannot connect to Ollama at {self.base_url}\n"
                "Make sure Ollama is running: `ollama serve`"
            )
        except requests.exceptions.Timeout:
            raise TimeoutError("Request to Ollama timed out")
    
    def check_model_available(self) -> bool:
        """Check if the model is available locally"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(m.get("name", "").startswith(self.model.split(":")[0]) 
                          for m in models)
            return False
        except:
            return False
    
    def pull_model(self) -> Generator[str, None, None]:
        """Pull the model if not available"""
        response = self._make_request(
            "api/pull",
            {"name": self.model},
            stream=True
        )
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                status = data.get("status", "")
                yield status
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = True
    ) -> Generator[str, None, None] | str:
        """Generate response from a single prompt"""
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "top_p": self.config.top_p,
                "repeat_penalty": self.config.repeat_penalty,
            }
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        response = self._make_request("api/generate", data, stream=stream)
        
        if stream:
            return self._stream_response(response)
        else:
            return response.json().get("response", "")
    
    def chat(
        self,
        messages: List[Message],
        stream: bool = True
    ) -> Generator[str, None, None] | str:
        """Chat with conversation history"""
        data = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "top_p": self.config.top_p,
                "repeat_penalty": self.config.repeat_penalty,
            }
        }
        
        response = self._make_request("api/chat", data, stream=stream)
        
        if stream:
            return self._stream_chat_response(response)
        else:
            return response.json().get("message", {}).get("content", "")
    
    def _stream_response(self, response) -> Generator[str, None, None]:
        """Stream response tokens"""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done", False):
                    break
    
    def _stream_chat_response(self, response) -> Generator[str, None, None]:
        """Stream chat response tokens"""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done", False):
                    break
    
    def should_search(self, query: str) -> bool:
        """Determine if the AI should search the web for this query"""
        check_prompt = f"""Analyze this user query and determine if it requires current/external information that you might not have.
        
Query: "{query}"

Respond with ONLY "YES" or "NO".
- YES if the query asks about: current events, specific facts you're unsure about, recent news, prices, weather, specific people/companies, URLs, or anything that might need verification.
- NO if the query is: general knowledge, coding help, creative writing, math, explanations of concepts, or things you're confident about.

Answer:"""
        
        response = self.generate(check_prompt, stream=False)
        return "YES" in response.upper()
    
    def extract_search_query(self, user_query: str) -> str:
        """Extract an optimized search query from user input"""
        prompt = f"""Convert this user question into an optimal Google search query.
Return ONLY the search query, nothing else.

User question: "{user_query}"

Search query:"""
        
        response = self.generate(prompt, stream=False)
        return response.strip().strip('"').strip("'")


def ask_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    stream: bool = True
) -> Generator[str, None, None] | str:
    """Simple function to ask the LLM"""
    llm = OllamaLLM()
    return llm.generate(prompt, system_prompt, stream)


def chat_llm(
    messages: List[Dict[str, str]],
    stream: bool = True
) -> Generator[str, None, None] | str:
    """Chat with message history"""
    llm = OllamaLLM()
    msg_objects = [Message(m["role"], m["content"]) for m in messages]
    return llm.chat(msg_objects, stream)


# Singleton instance
_llm_instance: Optional[OllamaLLM] = None

def get_llm() -> OllamaLLM:
    """Get or create LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = OllamaLLM()
    return _llm_instance