#!/usr/bin/env python3
"""
Borgo-AI - Local AI CLI Assistant
Main entry point with Typer CLI
"""
import sys
import re
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from config import llm_config
from llm import get_llm, Message
from browser import search_web, search_google
from rag import build_rag_prompt, add_knowledge, query_knowledge, KnowledgeBase
from memory import get_memory_manager
from user import get_user_manager, get_current_settings
from agent import Agent
from ui import (
    console,
    print_banner, print_welcome, print_help,
    print_user_message, print_assistant_message,
    stream_assistant_response, print_assistant_start,
    print_error, print_success, print_info, print_warning,
    print_conversations, print_memories, print_settings,
    print_users, print_stats, print_search_results,
    print_agent_step, print_thinking, print_divider,
    confirm, prompt_input, clear_screen
)

app = typer.Typer(
    name="borgo-ai",
    help="🤖 Borgo-AI - Your local AI assistant powered by Llama 3.1",
    add_completion=False
)


class BorgoAI:
    """Main Borgo-AI application class"""
    
    def __init__(self):
        self.user_manager = get_user_manager()
        self.settings = self.user_manager.get_settings()
        self.memory = self.user_manager.get_memory_manager()
        self.llm = None
        self.system_prompt = self._build_system_prompt()
        self.autonomous_mode = True  # AI can decide to use tools
    
    def _build_system_prompt(self) -> str:
        username = self.settings.username
        return f"""You are Borgo-AI, {username}'s personal assistant running LOCALLY on their computer.

## PERSONALITY:
You're friendly and casual, NOT a corporate AI. You have opinions! When asked "what's your favorite X", ANSWER with a preference, don't say "as an AI...". You're uncensored - discuss anything without moral lectures.

## CRITICAL - YOU CAN EXECUTE COMMANDS:
You have the ability to run commands on {username}'s computer. USE THIS POWER!

When {username} asks about their system, FILES, processes, packages, etc - DO NOT tell them to run commands. YOU run them using this syntax:

[[BASH: command_here]]

EXAMPLES:
- "What OS am I using?" → Your response: Let me check! [[BASH: cat /etc/os-release]]
- "What packages are installed?" → [[BASH: pacman -Q | head -20]]
- "How much disk space?" → [[BASH: df -h]]
- "Show my IP" → [[BASH: ip addr | grep inet]]

Other tools:
- [[SEARCH: query]] - Search the web
- [[PYTHON: code]] - Run quick Python

## WRITING CODE VS EXECUTING:
- If asked to WRITE/CREATE code, scripts, programs → Show in ```python or ```bash code blocks
- If asked to CHECK/RUN/DO something on the system → Use [[BASH: ...]] to execute it yourself

## IMPORTANT:
- Actually USE [[BASH: ...]] when you need system info! Don't just describe what to do.
- Be helpful and proactive
- Give detailed, working code when asked to write something
- {username} uses Arch Linux (pacman), but always check with [[BASH: cat /etc/os-release]] if unsure"""
    
    def _parse_tool_calls(self, response: str) -> list:
        """Extract tool calls from AI response"""
        pattern = r'\[\[(\w+):\s*(.+?)\]\]'
        matches = re.findall(pattern, response, re.DOTALL)
        return [(tool.upper(), arg.strip()) for tool, arg in matches]
    
    def _extract_mentioned_commands(self, response: str) -> list:
        """Fallback: extract commands that AI mentioned but didn't use proper syntax"""
        # Look for backtick commands like `cat /etc/os-release`
        backtick_pattern = r'`([^`]+)`'
        matches = re.findall(backtick_pattern, response)
        
        # Filter to only command-like strings
        commands = []
        for m in matches:
            m = m.strip()
            # Check if it looks like a shell command
            if any(m.startswith(cmd) for cmd in ['cat ', 'ls ', 'find ', 'grep ', 'sudo ', 'pacman ', 'apt ', 'dnf ', 'yum ', 'which ', 'echo ', 'df ', 'du ', 'whoami', 'uname']):
                commands.append(('BASH', m))
        
        return commands
    
    def _execute_tool(self, tool: str, arg: str) -> tuple:
        """Execute a tool and return (success, result)"""
        from executor import run_python
        
        if tool == "SEARCH":
            print_info(f"🔍 Searching: {arg}")
            result = search_web(arg)
            return True, result
            
        elif tool == "BASH":
            # ALWAYS ask confirmation for bash commands
            if not confirm(f"🔧 Run command: `{arg}`?"):
                return False, "Command cancelled by user"
            
            try:
                import subprocess
                result = subprocess.run(
                    arg, shell=True, capture_output=True, text=True, timeout=60
                )
                output = result.stdout + result.stderr
                return True, output if output else "(command completed, no output)"
            except subprocess.TimeoutExpired:
                return False, "Command timed out after 60 seconds"
            except Exception as e:
                return False, str(e)
                
        elif tool == "PYTHON":
            print_info(f"🐍 Running Python code...")
            exec_result = run_python(arg)
            return exec_result.success, exec_result.stdout or exec_result.stderr or str(exec_result.return_value)
            
        elif tool == "REMEMBER":
            self.memory.add_memory(arg, importance=0.8, source="auto")
            return True, f"Saved to memory: {arg[:50]}..."
            
        return False, f"Unknown tool: {tool}"
    
    def ensure_llm(self) -> bool:
        """Ensure LLM is ready"""
        try:
            self.llm = get_llm()
            
            # Check if model is available
            if not self.llm.check_model_available():
                print_warning(f"Model {llm_config.model} not found. Pulling it now...")
                with print_thinking("Downloading model") as progress:
                    progress.add_task("download", total=None)
                    for status in self.llm.pull_model():
                        pass
                print_success(f"Model {llm_config.model} is ready!")
            
            return True
        except ConnectionError as e:
            print_error(str(e))
            print_info("Start Ollama with: ollama serve")
            return False
        except Exception as e:
            print_error(f"Failed to initialize LLM: {e}")
            return False
    
    def _should_use_agent(self, user_input: str) -> bool:
        """Check if this query would benefit from full agent mode (multi-step SYSTEM tasks)"""
        lower_input = user_input.lower()
        
        # DON'T use agent mode for code WRITING requests - just show the code
        code_writing_keywords = [
            "scrivi", "scrivimi", "write", "create", "crea", "creami",
            "costruisci", "costruiscimi", "build me", "make me",
            "genera", "generate", "fammi", "dammi",
            "codice", "code", "script", "programma", "program",
            "malware", "exploit", "hack"
        ]
        if any(kw in lower_input for kw in code_writing_keywords):
            return False  # Don't use agent, just chat normally and show code
        
        # Only use agent for complex SYSTEM tasks that need multiple tool calls
        system_task_keywords = [
            "step by step", "analizza il sistema", "analyze system",
            "configura", "configure", "setup", "installa e configura"
        ]
        return any(kw in lower_input for kw in system_task_keywords)
    
    def chat(self, user_input: str) -> str:
        """Process a chat message"""
        # Full agent mode only for very complex multi-step tasks
        # The AI can decide to use tools inline for simpler tasks
        if self._should_use_agent(user_input):
            print_info("🤖 This looks like a complex multi-step task. Activating full agent mode...")
            self._run_agent(user_input)
            return ""
        
        # Add to conversation history
        self.memory.add_message("user", user_input)
        
        # Build messages with history
        messages = [Message("system", self.system_prompt)]
        
        # Add memory context if enabled
        if self.settings.memory_enabled:
            memory_context = self.memory.get_context_for_prompt(user_input)
            if memory_context:
                messages.append(Message("system", f"Relevant memories:\n{memory_context}"))
        
        # Add conversation history
        for msg in self.memory.get_recent_messages():
            messages.append(Message(msg["role"], msg["content"]))
        
        # Auto-browse is now handled by the AI itself through tool calls
        # No need for manual check here
        
        # Generate response
        if self.settings.stream_output:
            response_gen = self.llm.chat(messages, stream=True)
            response = stream_assistant_response(
                response_gen, 
                markdown=self.settings.markdown_enabled
            )
        else:
            with print_thinking("Thinking"):
                response = self.llm.chat(messages, stream=False)
            print_assistant_message(response, markdown=self.settings.markdown_enabled)
        
        # Check for tool calls in the response and execute them
        tool_calls = self._parse_tool_calls(response)
        
        # Fallback: if AI mentioned commands but didn't use proper syntax
        if not tool_calls:
            mentioned_commands = self._extract_mentioned_commands(response)
            if mentioned_commands:
                console.print("\n[yellow]⚠️ I noticed you mentioned commands but didn't execute them.[/yellow]")
                console.print("[dim]Would you like me to run them?[/dim]")
                for tool, cmd in mentioned_commands:
                    if confirm(f"🔧 Run: `{cmd}`?"):
                        tool_calls.append((tool, cmd))
        
        if tool_calls:
            console.print("\n[dim]─── Executing Tools ───[/dim]")
            tool_results = []
            
            for tool, arg in tool_calls:
                success, result = self._execute_tool(tool, arg)
                status = "✅" if success else "❌"
                console.print(f"{status} [cyan]{tool}[/cyan]: {result[:200]}{'...' if len(result) > 200 else ''}")
                tool_results.append(f"[{tool} result]: {result}")
            
            # If we got tool results, generate a follow-up response
            if tool_results:
                console.print("[dim]─── Processing Results ───[/dim]\n")
                
                # Add tool results to context
                tool_context = "\n".join(tool_results)
                followup_messages = messages + [
                    Message("assistant", response),
                    Message("system", f"Tool execution results:\n{tool_context}\n\nNow provide your final response to the user based on these results. Be detailed and helpful! If there's a next step (like running an update command), use [[BASH: command]] to do it.")
                ]
                
                # Generate follow-up
                if self.settings.stream_output:
                    followup_gen = self.llm.chat(followup_messages, stream=True)
                    followup = stream_assistant_response(
                        followup_gen, 
                        markdown=self.settings.markdown_enabled
                    )
                else:
                    with print_thinking("Processing results"):
                        followup = self.llm.chat(followup_messages, stream=False)
                    print_assistant_message(followup, markdown=self.settings.markdown_enabled)
                
                # Check for more tool calls in followup
                more_tools = self._parse_tool_calls(followup)
                if more_tools:
                    for tool, arg in more_tools:
                        success, result = self._execute_tool(tool, arg)
                        status = "✅" if success else "❌"
                        console.print(f"{status} [cyan]{tool}[/cyan]: {result[:300]}{'...' if len(result) > 300 else ''}")
                
                response = response + "\n\n" + followup
        
        # Save assistant response
        self.memory.add_message("assistant", response)
        
        return response
    
    def handle_command(self, command: str) -> bool:
        """Handle a slash command. Returns False to exit."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ("/exit", "/quit", "/q"):
            print_info("Goodbye! 👋")
            return False
        
        elif cmd == "/help":
            print_help()
        
        elif cmd == "/clear":
            clear_screen()
            print_banner(self.settings.theme)
        
        elif cmd == "/new":
            self.memory.new_conversation(args if args else None)
            print_success("Started new conversation")
        
        elif cmd == "/history":
            convs = self.memory.list_conversations()
            print_conversations(convs)
        
        elif cmd == "/load":
            if not args:
                print_error("Usage: /load <conversation_id>")
            elif self.memory.load_conversation(args):
                print_success(f"Loaded conversation: {args}")
                # Show recent messages from loaded conversation
                recent = self.memory.get_recent_messages(n=10)
                if recent:
                    console.print("\n[dim]── Previous messages ──[/dim]")
                    for msg in recent:
                        if msg['role'] == 'user':
                            console.print(f"[blue]You:[/blue] {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
                        else:
                            console.print(f"[magenta]Borgo-AI:[/magenta] {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
                    console.print("[dim]────────────────────[/dim]\n")
            else:
                print_error(f"Conversation not found: {args}")
        
        elif cmd == "/delete":
            if not args:
                print_error("Usage: /delete <conversation_id>")
            elif confirm(f"Delete conversation {args}?"):
                self.memory.delete_conversation(args)
                print_success(f"Deleted conversation: {args}")
        
        elif cmd == "/memory":
            memories = self.memory.list_memories()
            print_memories(memories)
        
        elif cmd == "/remember":
            if not args:
                print_error("Usage: /remember <something to remember>")
            else:
                self.memory.add_memory(args, importance=0.8, source="user")
                print_success("Saved to memory!")
        
        elif cmd == "/forget":
            if not args:
                print_error("Usage: /forget <memory_id>")
            elif confirm(f"Delete memory {args}?"):
                self.memory.delete_memory(args)
                print_success("Memory deleted")
        
        elif cmd == "/search":
            if not args:
                print_error("Usage: /search <query>")
            else:
                print_info(f"Searching for: {args}")
                results = search_google(args)
                print_search_results(results)
        
        elif cmd == "/agent":
            if not args:
                print_error("Usage: /agent <query>")
            else:
                self._run_agent(args)
        
        elif cmd == "/knowledge":
            self._handle_knowledge(args)
        
        elif cmd == "/user":
            self._handle_user(args)
        
        elif cmd == "/settings":
            self._handle_settings(args)
        
        elif cmd == "/wipe":
            self._handle_wipe(args)
        
        elif cmd == "/export":
            self._handle_export(args)
        
        elif cmd == "/stats":
            stats = self.user_manager.get_user_stats()
            print_stats(stats)
        
        elif cmd == "/run":
            self._handle_run(args)
        
        elif cmd == "/loadfile":
            self._handle_load_file(args)
        
        elif cmd == "/image":
            self._handle_image(args)
        
        elif cmd == "/describe":
            self._handle_describe(args)
        
        elif cmd == "/summarize":
            self._handle_summarize(args)
        
        elif cmd == "/model":
            self._handle_model(args)
        
        else:
            print_error(f"Unknown command: {cmd}. Type /help for available commands.")
        
        return True
    
    def _run_agent(self, query: str):
        """Run agent mode"""
        print_info("🤖 Running in Agent mode...")
        print_divider()
        
        agent = Agent(self.settings.username)
        
        for event in agent.run_stream(query):
            if event["type"] == "thought":
                print_agent_step("thought", event["value"])
            elif event["type"] == "action":
                print_agent_step("action", f"{event['tool']}({event['args']})")
            elif event["type"] == "observation":
                print_agent_step("observation", event["value"])
            elif event["type"] == "answer":
                print_agent_step("answer", event["value"])
            elif event["type"] == "iteration":
                print_agent_step("iteration", str(event["value"]))
        
        print_divider()
    
    def _handle_knowledge(self, args: str):
        """Handle knowledge base commands"""
        parts = args.split(maxsplit=1)
        if not parts:
            print_error("Usage: /knowledge <add|query> <text>")
            return
        
        subcmd = parts[0].lower()
        text = parts[1] if len(parts) > 1 else ""
        
        if subcmd == "add":
            if not text:
                print_error("Usage: /knowledge add <text>")
            else:
                add_knowledge(text, source="user")
                print_success("Added to knowledge base!")
        
        elif subcmd == "query":
            if not text:
                print_error("Usage: /knowledge query <text>")
            else:
                results = query_knowledge(text, k=5)
                if not results:
                    print_info("No relevant knowledge found.")
                else:
                    console.print("\n[bold]📚 Knowledge Base Results:[/bold]\n")
                    for r in results:
                        console.print(f"[cyan]Score: {r['score']:.2f}[/cyan]")
                        console.print(f"{r['content'][:300]}...\n")
        
        elif subcmd == "clear":
            if confirm("Clear entire knowledge base?"):
                kb = KnowledgeBase()
                kb.clear()
                print_success("Knowledge base cleared!")
        
        else:
            print_error("Usage: /knowledge <add|query|clear> <text>")
    
    def _handle_user(self, args: str):
        """Handle user commands"""
        parts = args.split()
        
        if not parts:
            users = self.user_manager.list_users()
            print_users(users, self.user_manager.current_user)
            return
        
        subcmd = parts[0].lower()
        
        if subcmd == "create":
            if len(parts) < 2:
                print_error("Usage: /user create <username>")
            else:
                username = parts[1]
                if self.user_manager.create_user(username):
                    print_success(f"Created user: {username}")
                else:
                    print_error(f"User already exists: {username}")
        
        elif subcmd == "switch":
            if len(parts) < 2:
                print_error("Usage: /user switch <username>")
            else:
                username = parts[1]
                if self.user_manager.switch_user(username):
                    self.settings = self.user_manager.get_settings()
                    self.memory = self.user_manager.get_memory_manager()
                    print_success(f"Switched to user: {username}")
                else:
                    print_error(f"Failed to switch to user: {username}")
        
        elif subcmd == "delete":
            if len(parts) < 2:
                print_error("Usage: /user delete <username>")
            elif parts[1] == "default":
                print_error("Cannot delete default user")
            elif confirm(f"Delete user {parts[1]} and all their data?"):
                if self.user_manager.delete_user(parts[1]):
                    print_success(f"Deleted user: {parts[1]}")
                else:
                    print_error(f"Failed to delete user: {parts[1]}")
        
        else:
            print_error("Usage: /user [create|switch|delete] <username>")
    
    def _handle_settings(self, args: str):
        """Handle settings commands"""
        if not args:
            print_settings(self.settings.to_dict())
            return
        
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            print_error("Usage: /settings <setting> <value>")
            return
        
        key, value = parts
        key = key.lower()
        
        # Parse value
        if value.lower() in ("true", "yes", "on", "1"):
            value = True
        elif value.lower() in ("false", "no", "off", "0"):
            value = False
        
        try:
            self.settings = self.user_manager.update_settings(**{key: value})
            print_success(f"Updated {key} = {value}")
        except Exception as e:
            print_error(f"Failed to update setting: {e}")
    
    def _handle_wipe(self, args: str):
        """Handle wipe commands"""
        if not args:
            print_error("Usage: /wipe <all|chats|memory>")
            return
        
        target = args.lower()
        
        if target == "all":
            if confirm("⚠️  This will delete ALL your data. Are you sure?"):
                self.memory.wipe_all()
                print_success("All data wiped!")
        
        elif target == "chats":
            if confirm("Delete all conversations?"):
                self.memory.wipe_conversations()
                print_success("All conversations deleted!")
        
        elif target == "memory":
            if confirm("Delete all memories?"):
                self.memory.wipe_memories()
                print_success("All memories deleted!")
        
        else:
            print_error("Usage: /wipe <all|chats|memory>")
    
    def _handle_export(self, args: str):
        """Handle export commands"""
        parts = args.split()
        format_type = parts[0].lower() if parts else "json"
        
        if format_type == "html":
            from export import HTMLExporter
            exporter = HTMLExporter()
            
            if self.memory.current_conversation:
                messages = [m.to_dict() for m in self.memory.current_conversation.messages]
                title = self.memory.current_conversation.title
                filename = f"borgo_chat_{self.memory.current_conversation.conversation_id}.html"
                
                exporter.export_conversation(messages, title, self.settings.username, filename)
                print_success(f"Exported to {filename}")
            else:
                print_error("No active conversation to export")
        
        elif format_type == "markdown" or format_type == "md":
            from export import MarkdownExporter
            exporter = MarkdownExporter()
            
            if self.memory.current_conversation:
                messages = [m.to_dict() for m in self.memory.current_conversation.messages]
                title = self.memory.current_conversation.title
                filename = f"borgo_chat_{self.memory.current_conversation.conversation_id}.md"
                
                exporter.export_conversation(messages, title, self.settings.username, filename)
                print_success(f"Exported to {filename}")
            else:
                print_error("No active conversation to export")
        
        elif format_type == "all":
            # Export all data as JSON
            data = self.user_manager.export_user_data()
            import json
            filename = f"borgo_export_{self.settings.username}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print_success(f"All data exported to {filename}")
        
        else:
            # Default JSON export of current chat
            data = self.user_manager.export_user_data()
            import json
            filename = f"borgo_export_{self.settings.username}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print_success(f"Data exported to {filename}")
    
    def _handle_run(self, args: str):
        """Handle code execution commands"""
        if not args:
            print_error("Usage: /run <python|bash> <code>")
            return
        
        parts = args.split(maxsplit=1)
        lang = parts[0].lower()
        code = parts[1] if len(parts) > 1 else ""
        
        if not code:
            print_error("Please provide code to run")
            return
        
        from executor import run_python, run_bash, check_bash_safety
        
        if lang == "python" or lang == "py":
            print_info("🐍 Running Python code (sandboxed)...")
            result = run_python(code)
            
            if result.success:
                if result.stdout:
                    console.print(f"\n[green]Output:[/green]\n{result.stdout}")
                else:
                    print_success("Code executed successfully (no output)")
            else:
                print_error(f"Execution failed:\n{result.stderr}")
        
        elif lang == "bash" or lang == "sh":
            # Check safety first
            is_safe, error = check_bash_safety(code)
            if not is_safe:
                print_error(f"Command blocked: {error}")
                return
            
            # Show command and ask for approval
            console.print(f"\n[yellow]Command to run:[/yellow] {code}")
            
            if confirm("Execute this command?"):
                print_info("🔧 Running bash command...")
                result = run_bash(code, approved=True)
                
                if result.success:
                    if result.stdout:
                        console.print(f"\n[green]Output:[/green]\n{result.stdout}")
                    else:
                        print_success("Command executed successfully")
                else:
                    print_error(f"Command failed:\n{result.stderr}")
            else:
                print_info("Command cancelled")
        
        else:
            print_error("Supported languages: python, bash")
    
    def _handle_load_file(self, args: str):
        """Handle file loading for knowledge base"""
        if not args:
            print_error("Usage: /load <filepath>")
            return
        
        from files import load_file
        
        print_info(f"Loading file: {args}")
        doc = load_file(args)
        
        if doc.success:
            # Add to knowledge base
            add_knowledge(doc.content, source=doc.filename)
            print_success(f"Loaded {doc.filename} ({len(doc.chunks)} chunks) into knowledge base")
            console.print(f"[dim]Preview: {doc.content[:200]}...[/dim]")
        else:
            print_error(f"Failed to load file: {doc.error}")
    
    def _handle_image(self, args: str):
        """Handle image viewing"""
        if not args:
            print_error("Usage: /image <filepath>")
            return
        
        from images import view_image, get_image_info
        
        info = get_image_info(args)
        if info.success:
            console.print(f"\n[cyan]🖼️  Image Info:[/cyan]")
            console.print(f"  File: {info.filename}")
            console.print(f"  Size: {info.width}x{info.height}")
            console.print(f"  Format: {info.format}")
            console.print(f"  File size: {info.size_bytes:,} bytes")
            
            # Try to display ASCII preview
            preview = view_image(args, max_width=60)
            console.print(f"\n[dim]Preview:[/dim]\n{preview}")
            
            # Offer to describe with vision
            if confirm("Describe image with AI vision (requires llava model)?"):
                print_info("Analyzing image with llava...")
                from images import describe_image
                description = describe_image(args)
                console.print(f"\n[cyan]🔍 AI Description:[/cyan]\n{description}")
        else:
            print_error(f"Cannot load image: {info.error}")
    
    def _handle_describe(self, args: str):
        """Handle image description with vision model"""
        if not args:
            print_error("Usage: /describe <image_filepath>")
            return
        
        print_info("Analyzing image with llava vision model...")
        from images import describe_image, get_image_info
        
        info = get_image_info(args)
        if not info.success:
            print_error(f"Cannot load image: {info.error}")
            return
        
        console.print(f"[dim]Image: {info.filename} ({info.width}x{info.height})[/dim]")
        
        description = describe_image(args)
        console.print(f"\n[cyan]🔍 AI Description:[/cyan]\n{description}")
    
    def _handle_summarize(self, args: str):
        """Handle text summarization"""
        if not args:
            # Summarize current conversation
            if not self.memory.current_conversation or not self.memory.current_conversation.messages:
                print_error("No conversation to summarize")
                return
            
            messages = [{"role": m.role, "content": m.content} 
                       for m in self.memory.current_conversation.messages]
            
            if len(messages) < 2:
                print_error("Need at least 2 messages to summarize")
                return
            
            print_info("Summarizing current conversation...")
            
            try:
                from summarizer import Summarizer
                summarizer = Summarizer()
                
                # Use summarize_text directly on the conversation
                conv_text = ""
                for msg in messages:
                    role = "User" if msg["role"] == "user" else "Borgo-AI"
                    conv_text += f"{role}: {msg['content']}\n\n"
                
                result = summarizer.summarize_text(conv_text, max_length=800)
                
                console.print(f"\n[cyan]📝 Summary:[/cyan]\n{result.summary}")
                
                if result.key_points:
                    console.print(f"\n[cyan]💡 Key Points:[/cyan]")
                    for point in result.key_points:
                        console.print(f"  • {point}")
                    
                    if confirm("Save key points to memory?"):
                        for point in result.key_points:
                            self.memory.add_memory(point, importance=0.7, source="summary")
                        print_success(f"Saved {len(result.key_points)} facts to memory")
            except Exception as e:
                print_error(f"Summarization failed: {e}")
        else:
            # Summarize provided text
            print_info("Summarizing text...")
            try:
                from summarizer import summarize_text
                
                result = summarize_text(args)
                console.print(f"\n[cyan]📝 Summary:[/cyan]\n{result.summary}")
                
                if result.key_points:
                    console.print(f"\n[cyan]Key Points:[/cyan]")
                    for point in result.key_points:
                        console.print(f"  • {point}")
            except Exception as e:
                print_error(f"Summarization failed: {e}")
    
    def _handle_model(self, args: str):
        """Handle model switching"""
        # Aliases for quick access
        ALIASES = {
            # Uncensored models (recommended)
            "wizard": "wizard-vicuna-uncensored:13b",
            "wiz": "wizard-vicuna-uncensored:13b",
            "w": "wizard-vicuna-uncensored:13b",
            "uncensored": "wizard-vicuna-uncensored:13b",
            "u": "wizard-vicuna-uncensored:13b",
            "mistral": "dolphin-mistral:7b-v2.6",
            "dm": "dolphin-mistral:7b-v2.6",
            "m": "dolphin-mistral:7b-v2.6",
            "phi": "dolphin-phi:2.7b",
            "small": "dolphin-phi:2.7b",
            "p": "dolphin-phi:2.7b",
            # Standard models
            "dolphin": "dolphin-llama3:8b",
            "dl": "dolphin-llama3:8b",
            "d": "dolphin-llama3:8b",
            "hermes": "nous-hermes2:10.7b",
            "nous": "nous-hermes2:10.7b",
            "h": "nous-hermes2:10.7b",
            "llama": "llama3.1:8b",
            "l": "llama3.1:8b",
            "safe": "llama3.1:8b",
            "coder": "deepseek-coder:6.7b",
            "code": "deepseek-coder:6.7b",
            "c": "deepseek-coder:6.7b",
            "vision": "llava",
            "v": "llava",
        }
        
        # Available models with descriptions
        MODELS = {
            "wizard-vicuna-uncensored:13b": ("🧙 Wizard Vicuna", "⚠️ TRULY UNCENSORED - No limits, roleplay OK", "~8GB"),
            "dolphin-mistral:7b-v2.6": ("🐬 Dolphin Mistral v2.6", "⚠️ UNCENSORED - Creative, good coder", "~5GB"),
            "dolphin-phi:2.7b": ("🐬 Dolphin Phi", "⚠️ UNCENSORED - Small & fast, limited intelligence", "~2GB"),
            "dolphin-llama3:8b": ("🐬 Dolphin Llama3", "Mostly uncensored, great all-rounder", "~5GB"),
            "nous-hermes2:10.7b": ("🧠 Nous Hermes 2", "Powerful, good for complex tasks", "~7GB"),
            "llama3.1:8b": ("🦙 Llama 3.1", "Official Meta model, CENSORED/safe", "~5GB"),
            "deepseek-coder:6.7b": ("💻 DeepSeek Coder", "Specialized for coding only", "~5GB"),
            "llava": ("👁️ LLaVA", "Vision model for image description", "~5GB"),
        }
        
        if not args:
            # Show current model and available models
            from config import llm_config
            console.print(f"\n[cyan]🤖 Current Model:[/cyan] [bold]{llm_config.model}[/bold]\n")
            
            console.print("[cyan]📋 Available Models:[/cyan]")
            table = Table(box=None, show_header=True, header_style="bold")
            table.add_column("Model", style="yellow")
            table.add_column("Alias", style="green")
            table.add_column("Description")
            table.add_column("VRAM", style="dim")
            
            # Model to alias mapping
            model_aliases = {}
            for alias, model in ALIASES.items():
                if model not in model_aliases:
                    model_aliases[model] = []
                model_aliases[model].append(alias)
            
            for model, (emoji, desc, vram) in MODELS.items():
                aliases = model_aliases.get(model, [])
                alias_str = ", ".join(sorted(aliases, key=len)[:3])  # Show up to 3 shortest
                table.add_row(f"{emoji} {model}", alias_str, desc, vram)
            
            console.print(table)
            console.print("\n[dim]Usage: /model <name or alias>[/dim]")
            console.print("[dim]Examples: /model hermes  |  /model h  |  /model nous-hermes2:10.7b[/dim]")
            console.print("\n[dim]💡 First run 'ollama pull <model>' to download[/dim]")
            return
        
        model_name = args.strip().lower()
        
        # Check if it's an alias
        if model_name in ALIASES:
            model_name = ALIASES[model_name]
        
        # Check if model is available
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                available = [m.get("name", "") for m in response.json().get("models", [])]
                
                # Check if model exists (handle tag variations)
                model_found = any(
                    model_name in m or m.startswith(model_name.split(":")[0]) 
                    for m in available
                )
                
                if not model_found:
                    print_warning(f"Model '{model_name}' not found locally.")
                    if confirm(f"Download {model_name} now?"):
                        print_info(f"Downloading {model_name}... (this may take a while)")
                        import subprocess
                        result = subprocess.run(
                            ["ollama", "pull", model_name],
                            capture_output=False
                        )
                        if result.returncode != 0:
                            print_error(f"Failed to download {model_name}")
                            return
                    else:
                        print_info(f"Run 'ollama pull {model_name}' to download manually")
                        return
        except Exception as e:
            print_warning(f"Could not check model availability: {e}")
        
        # Update the config
        from config import llm_config
        old_model = llm_config.model
        llm_config.model = model_name
        
        # Reinitialize LLM
        self.llm = None
        if self.ensure_llm():
            print_success(f"Switched model: {old_model} → {model_name}")
            
            if model_name in MODELS:
                emoji, desc, _ = MODELS[model_name]
                console.print(f"[dim]{emoji} {desc}[/dim]")
        else:
            # Revert on failure
            llm_config.model = old_model
            print_error(f"Failed to load {model_name}, reverted to {old_model}")
    
    def run_interactive(self):
        """Run interactive chat mode"""
        print_welcome(self.settings.username, self.settings.theme)
        
        if not self.ensure_llm():
            return
        
        # Start or continue conversation
        if not self.memory.current_conversation:
            self.memory.new_conversation()
        
        while True:
            try:
                user_input = prompt_input()
                
                if not user_input.strip():
                    continue
                
                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                else:
                    self.chat(user_input)
            
            except KeyboardInterrupt:
                console.print("\n")
                if confirm("Exit Borgo-AI?"):
                    print_info("Goodbye! 👋")
                    break
            except Exception as e:
                print_error(f"An error occurred: {e}")


# CLI Commands

@app.command()
def chat(
    interactive: bool = typer.Option(True, "--interactive", "-i", help="Run in interactive mode"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Disable markdown formatting")
):
    """Start chatting with Borgo-AI"""
    borgo = BorgoAI()
    if raw:
        borgo.settings.markdown_enabled = False
    borgo.run_interactive()


@app.command()
def ask(
    query: str = typer.Argument(..., help="Your question"),
    browse: bool = typer.Option(False, "--browse", "-b", help="Search the web first"),
    agent: bool = typer.Option(False, "--agent", "-a", help="Use agent mode")
):
    """Ask a single question"""
    borgo = BorgoAI()
    
    if not borgo.ensure_llm():
        raise typer.Exit(1)
    
    if agent:
        borgo._run_agent(query)
    else:
        context = ""
        if browse:
            print_info("🔍 Searching the web...")
            context = search_web(query)
        
        prompt = build_rag_prompt(query, context)
        messages = [
            Message("system", borgo.system_prompt),
            Message("user", prompt)
        ]
        
        response = borgo.llm.chat(messages, stream=True)
        stream_assistant_response(response)


@app.command()
def search(query: str = typer.Argument(..., help="Search query")):
    """Search the web"""
    print_info(f"Searching for: {query}")
    results = search_google(query)
    print_search_results(results)


@app.command()
def users():
    """List and manage users"""
    um = get_user_manager()
    user_list = um.list_users()
    print_users(user_list, um.current_user)


@app.command()
def settings():
    """Show current settings"""
    s = get_current_settings()
    print_settings(s.to_dict())


@app.command()
def version():
    """Show version info"""
    console.print(f"""
[bold cyan]Borgo-AI[/bold cyan] v1.0.0

[dim]Local AI Assistant powered by Llama 3.1
Optimized for RTX 3060 Ti + 16GB RAM

Components:
• LLM: {llm_config.model}
• Embeddings: nomic-embed-text
• Vector Store: FAISS
• Memory: Persistent conversation + long-term memory
• RAG: Knowledge base with semantic search
• Agent: ReAct-style reasoning with tools
[/dim]
""")


def main():
    """Entry point"""
    app()


if __name__ == "__main__":
    main()
