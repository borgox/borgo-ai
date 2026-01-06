"""
Agent Module - Agentic AI capabilities for borgo-ai
"""
import json
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .config import agent_config
from .llm import get_llm, Message
from .browser import search_web, fetch_url, search_google
from .memory import get_memory_manager
from .rag import query_knowledge, add_knowledge


class ToolType(Enum):
    """Types of tools available to the agent"""
    SEARCH = "search_web"
    READ_URL = "read_url"
    REMEMBER = "remember"
    RECALL = "recall"
    CALCULATE = "calculate"
    GET_TIME = "get_time"
    ADD_KNOWLEDGE = "add_knowledge"
    QUERY_KNOWLEDGE = "query_knowledge"
    RUN_PYTHON = "run_python"
    VIEW_IMAGE = "view_image"
    SUMMARIZE = "summarize"


@dataclass
class ToolCall:
    """Represents a tool call by the agent"""
    tool: str
    args: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentStep:
    """A single step in the agent's reasoning"""
    thought: str
    action: Optional[ToolCall] = None
    observation: Optional[str] = None


@dataclass
class AgentResult:
    """Final result from the agent"""
    answer: str
    steps: List[AgentStep] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 0


class AgentTools:
    """Collection of tools available to the agent"""
    
    def __init__(self, username: str = "default"):
        self.username = username
        self.tools = {
            "search_web": self._search_web,
            "read_url": self._read_url,
            "remember": self._remember,
            "recall": self._recall,
            "calculate": self._calculate,
            "get_time": self._get_time,
            "add_knowledge": self._add_knowledge,
            "query_knowledge": self._query_knowledge,
            "run_python": self._run_python,
            "run_bash": self._run_bash,
            "view_image": self._view_image,
            "summarize": self._summarize,
            "load_file": self._load_file,
            "get_system_info": self._get_system_info,
        }
    
    def get_tool_descriptions(self) -> str:
        """Get descriptions of available tools"""
        return """Available Tools:

1. search_web(query: str) -> str
   Search the internet for information (GET requests only, safe).
   Use when you need current information, facts, news, or anything you're unsure about.

2. read_url(url: str) -> str
   Read the content of a specific webpage (GET only, safe).
   Use when you have a specific URL to read.

3. remember(content: str, importance: float) -> str
   Save important information to long-term memory. Importance is 0-1.
   Use when the user tells you something important to remember.

4. recall(query: str) -> str
   Search your long-term memories for relevant information.
   Use when you need to remember something from past conversations.

5. calculate(expression: str) -> str
   Evaluate a mathematical expression. Returns the result.
   Use for any calculations.

6. get_time() -> str
   Get the current date and time.
   Use when asked about current time/date.

7. add_knowledge(content: str, source: str) -> str
   Add information to the knowledge base for RAG.
   Use when the user wants to add reference material.

8. query_knowledge(query: str) -> str
   Search the knowledge base.
   Use to find information from added documents.

9. run_python(code: str) -> str
   Execute Python code safely (sandboxed - no file/network access).
   Use for calculations, data processing, or testing code snippets.

10. run_bash(command: str) -> str
    Execute a bash command (REQUIRES USER APPROVAL).
    Use for: checking system info, file operations, running scripts.
    Examples: "cat /etc/os-release", "ls -la", "df -h", "whoami"
    NOTE: Dangerous commands (rm -rf, sudo, etc.) will be blocked.

11. get_system_info() -> str
    Get basic system information (OS, kernel, user, etc).
    Use when you need to know about the user's system.

12. view_image(filepath: str) -> str
    View information about an image file.
    Use when the user asks about an image.

13. summarize(text: str) -> str
    Summarize a long piece of text.
    Use when you need to condense information.

14. load_file(filepath: str) -> str
    Load content from a file (PDF, TXT, MD, DOCX, etc).
    Use when the user wants to reference a document."""
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolCall:
        """Execute a tool"""
        if tool_name not in self.tools:
            return ToolCall(
                tool=tool_name,
                args=args,
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
        
        try:
            result = self.tools[tool_name](**args)
            return ToolCall(
                tool=tool_name,
                args=args,
                result=str(result),
                success=True
            )
        except Exception as e:
            return ToolCall(
                tool=tool_name,
                args=args,
                success=False,
                error=str(e)
            )
    
    def _search_web(self, query: str) -> str:
        return search_web(query)
    
    def _read_url(self, url: str) -> str:
        page = fetch_url(url)
        if page.success:
            return f"Title: {page.title}\n\n{page.content}"
        return f"Failed to read URL: {page.error}"
    
    def _remember(self, content: str, importance: float = 0.7) -> str:
        mm = get_memory_manager(self.username)
        mm.add_memory(content, importance, source="agent")
        return f"Remembered: {content[:100]}..."
    
    def _recall(self, query: str) -> str:
        mm = get_memory_manager(self.username)
        memories = mm.recall_memories(query, k=5)
        if not memories:
            return "No relevant memories found."
        
        result = "Recalled memories:\n"
        for mem in memories:
            result += f"- {mem['content']} (relevance: {mem['score']:.2f})\n"
        return result
    
    def _calculate(self, expression: str) -> str:
        # Safe math evaluation
        try:
            # Only allow safe operations
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expression):
                return "Invalid expression - only numbers and basic operators allowed"
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"
    
    def _get_time(self) -> str:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S (%A)")
    
    def _add_knowledge(self, content: str, source: str = "agent") -> str:
        add_knowledge(content, source)
        return f"Added to knowledge base: {content[:100]}..."
    
    def _query_knowledge(self, query: str) -> str:
        results = query_knowledge(query, k=3)
        if not results:
            return "No relevant knowledge found."
        
        output = "From knowledge base:\n"
        for r in results:
            output += f"- {r['content'][:200]}... (score: {r['score']:.2f})\n"
        return output
    
    def _run_python(self, code: str) -> str:
        """Execute Python code safely"""
        try:
            from .executor import run_python
            result = run_python(code)
            
            if result.success:
                output = result.stdout
                if result.return_value is not None:
                    output += f"\nReturn value: {result.return_value}"
                return output if output else "Code executed successfully (no output)"
            else:
                return f"Error: {result.stderr}"
        except ImportError:
            return "Code execution module not available"
        except Exception as e:
            return f"Error: {e}"
    
    def _view_image(self, filepath: str) -> str:
        """Get information about an image"""
        try:
            from .images import get_image_info
            info = get_image_info(filepath)
            
            if info.success:
                return f"Image: {info.filename}\nSize: {info.width}x{info.height}\nFormat: {info.format}\nFile size: {info.size_bytes} bytes"
            else:
                return f"Error: {info.error}"
        except ImportError:
            return "Image module not available"
        except Exception as e:
            return f"Error: {e}"
    
    def _summarize(self, text: str) -> str:
        """Summarize text"""
        try:
            from .summarizer import summarize_text
            result = summarize_text(text)
            return result.summary
        except ImportError:
            return "Summarizer module not available"
        except Exception as e:
            return f"Error: {e}"
    
    def _run_bash(self, command: str) -> str:
        """Execute bash command (with user approval)"""
        try:
            from .executor import run_bash, check_bash_safety
            from .ui import confirm, console
            
            # Check safety first
            is_safe, error = check_bash_safety(command)
            if not is_safe:
                return f"Command blocked for safety: {error}"
            
            # Ask user for approval
            console.print(f"\n[yellow]🔧 Agent wants to run:[/yellow] {command}")
            if not confirm("Allow this command?"):
                return "Command rejected by user"
            
            result = run_bash(command, approved=True)
            
            if result.success:
                output = result.stdout.strip() if result.stdout else "(no output)"
                return f"Command output:\n{output}"
            else:
                return f"Command failed: {result.stderr}"
        except ImportError:
            return "Bash execution module not available"
        except Exception as e:
            return f"Error: {e}"
    
    def _get_system_info(self) -> str:
        """Get basic system information"""
        import platform
        import os
        
        info = []
        info.append(f"OS: {platform.system()} {platform.release()}")
        info.append(f"Platform: {platform.platform()}")
        info.append(f"User: {os.getenv('USER', 'unknown')}")
        info.append(f"Home: {os.path.expanduser('~')}")
        info.append(f"Shell: {os.getenv('SHELL', 'unknown')}")
        info.append(f"Python: {platform.python_version()}")
        
        return "\n".join(info)
    
    def _load_file(self, filepath: str) -> str:
        """Load file content"""
        try:
            from .files import load_file
            doc = load_file(filepath)
            
            if doc.success:
                return f"File: {doc.filename}\n\n{doc.content[:2000]}{'...' if len(doc.content) > 2000 else ''}"
            else:
                return f"Error: {doc.error}"
        except ImportError:
            return "File loader module not available"
        except Exception as e:
            return f"Error: {e}"


class Agent:
    """ReAct-style agent that can use tools"""
    
    def __init__(self, username: str = "default"):
        self.username = username
        self.llm = get_llm()
        self.tools = AgentTools(username)
        self.max_iterations = agent_config.max_iterations
    
    def _build_system_prompt(self) -> str:
        return f"""You are Borgo-AI, an intelligent and PROACTIVE AI assistant with access to powerful tools.
You use a ReAct (Reasoning + Acting) approach to solve problems step by step.

{self.tools.get_tool_descriptions()}

## Response Format

For each step, respond in this EXACT format:

THOUGHT: [Your reasoning - be specific about WHAT you're doing and WHY]
ACTION: [tool_name]
ARGS: {{"arg1": "value1", "arg2": "value2"}}

OR if you have enough information to answer:

THOUGHT: [Your final reasoning]
FINAL_ANSWER: [Your DETAILED and HELPFUL answer to the user]

## Important Guidelines
1. BE PROACTIVE - use multiple tools to gather complete information
2. For system tasks, use get_system_info first, then run_bash for specific info
3. NEVER give a short FINAL_ANSWER - be detailed, helpful, and thorough
4. If a task involves the system, ACTUALLY check things using tools
5. Suggest follow-up actions the user might want
6. After tool observations, CONTINUE until you have a complete answer
7. For updates/installs, provide the exact commands and ask to run them
6. If a tool fails, try a different approach"""
    
    def _parse_response(self, response: str) -> Dict:
        """Parse the agent's response"""
        result = {
            "thought": "",
            "action": None,
            "args": {},
            "final_answer": None
        }
        
        # Extract thought
        thought_match = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|FINAL_ANSWER:|$)", response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()
        
        # Check for final answer
        final_match = re.search(r"FINAL_ANSWER:\s*(.+?)$", response, re.DOTALL)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result
        
        # Extract action
        action_match = re.search(r"ACTION:\s*(\w+)", response)
        if action_match:
            result["action"] = action_match.group(1).strip()
        
        # Extract args
        args_match = re.search(r"ARGS:\s*(\{.+?\})", response, re.DOTALL)
        if args_match:
            try:
                result["args"] = json.loads(args_match.group(1))
            except json.JSONDecodeError:
                # Try to extract simple args
                pass
        
        return result
    
    def run(self, query: str, context: str = "") -> AgentResult:
        """Run the agent on a query"""
        steps = []
        tools_used = []
        
        messages = [
            Message("system", self._build_system_prompt()),
        ]
        
        # Add context if provided
        if context:
            messages.append(Message("user", f"Context:\n{context}\n\nQuery: {query}"))
        else:
            messages.append(Message("user", query))
        
        for iteration in range(self.max_iterations):
            # Get LLM response
            response = self.llm.chat(messages, stream=False)
            
            # Parse response
            parsed = self._parse_response(response)
            
            step = AgentStep(thought=parsed["thought"])
            
            # Check for final answer
            if parsed["final_answer"]:
                steps.append(step)
                return AgentResult(
                    answer=parsed["final_answer"],
                    steps=steps,
                    tools_used=list(set(tools_used)),
                    iterations=iteration + 1
                )
            
            # Execute tool if specified
            if parsed["action"]:
                tool_call = self.tools.execute(parsed["action"], parsed["args"])
                step.action = tool_call
                step.observation = tool_call.result if tool_call.success else tool_call.error
                
                tools_used.append(parsed["action"])
                
                # Add observation to messages
                messages.append(Message("assistant", response))
                messages.append(Message("user", f"OBSERVATION: {step.observation}"))
            
            steps.append(step)
        
        # Max iterations reached
        return AgentResult(
            answer="I wasn't able to complete this task within the allowed steps. Here's what I found:\n" + 
                   "\n".join(s.thought for s in steps if s.thought),
            steps=steps,
            tools_used=list(set(tools_used)),
            iterations=self.max_iterations
        )
    
    def run_stream(self, query: str, context: str = ""):
        """Run the agent with streaming output"""
        steps = []
        tools_used = []
        
        messages = [
            Message("system", self._build_system_prompt()),
        ]
        
        if context:
            messages.append(Message("user", f"Context:\n{context}\n\nQuery: {query}"))
        else:
            messages.append(Message("user", query))
        
        for iteration in range(self.max_iterations):
            # Yield iteration info
            yield {"type": "iteration", "value": iteration + 1}
            
            # Get LLM response (non-streaming for parsing)
            response = self.llm.chat(messages, stream=False)
            
            parsed = self._parse_response(response)
            
            # Yield thought
            if parsed["thought"]:
                yield {"type": "thought", "value": parsed["thought"]}
            
            # Check for final answer
            if parsed["final_answer"]:
                yield {"type": "answer", "value": parsed["final_answer"]}
                return
            
            # Execute tool
            if parsed["action"]:
                yield {"type": "action", "tool": parsed["action"], "args": parsed["args"]}
                
                tool_call = self.tools.execute(parsed["action"], parsed["args"])
                tools_used.append(parsed["action"])
                
                yield {
                    "type": "observation",
                    "value": tool_call.result if tool_call.success else f"Error: {tool_call.error}"
                }
                
                messages.append(Message("assistant", response))
                messages.append(Message("user", f"OBSERVATION: {tool_call.result if tool_call.success else tool_call.error}"))
        
        yield {"type": "max_iterations", "value": self.max_iterations}


def run_agent(query: str, username: str = "default", context: str = "") -> AgentResult:
    """Convenience function to run the agent"""
    agent = Agent(username)
    return agent.run(query, context)
