"""
UI Module - Beautiful CLI interface for borgo-ai
"""
import sys
import re
from typing import Optional, Generator
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich.theme import Theme

# Custom theme
BORGO_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold blue",
    "assistant": "bold magenta",
    "system": "dim white",
    "highlight": "bold yellow",
    "muted": "dim",
})

console = Console(theme=BORGO_THEME)


# ASCII Art Banners
BANNERS = {
    "cyber": r"""
[bold cyan]
 ██████╗  ██████╗ ██████╗  ██████╗  ██████╗        █████╗ ██╗
 ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗      ██╔══██╗██║
 ██████╔╝██║   ██║██████╔╝██║  ███╗██║   ██║█████╗███████║██║
 ██╔══██╗██║   ██║██╔══██╗██║   ██║██║   ██║╚════╝██╔══██║██║
 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝      ██║  ██║██║
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝       ╚═╝  ╚═╝╚═╝
[/bold cyan]
[dim cyan]═══════════════════════════════════════════════════════════════[/dim cyan]
[bold white]          🤖 Local AI Assistant • Powered by Llama 3.1[/bold white]
[dim cyan]═══════════════════════════════════════════════════════════════[/dim cyan]
""",

    "minimal": r"""
[bold white]
  ╔═══════════════════════════════════════════╗
  ║           B O R G O - A I                 ║
  ║         Local AI Assistant                ║
  ╚═══════════════════════════════════════════╝
[/bold white]
""",

    "retro": r"""
[bold green]
    ____                           ___    ____
   / __ )____  _________ _____    /   |  /  _/
  / __  / __ \/ ___/ __ `/ __ \  / /| |  / /  
 / /_/ / /_/ / /  / /_/ / /_/ / / ___ |_/ /   
/_____/\____/_/   \__, /\____/ /_/  |_/___/   
                 /____/                       
[/bold green]
[green]▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀[/green]
[bold]        >> TERMINAL AI INTERFACE v1.0 <<[/bold]
[green]▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀[/green]
"""
}


def print_banner(theme: str = "cyber"):
    """Print the welcome banner"""
    banner = BANNERS.get(theme, BANNERS["cyber"])
    console.print(banner)


def print_welcome(username: str, theme: str = "cyber"):
    """Print welcome message with banner"""
    console.clear()
    print_banner(theme)
    console.print(f"\n[dim]Welcome back, [bold cyan]{username}[/bold cyan]! Type [bold]/help[/bold] for commands.[/dim]\n")


def print_help():
    """Print help information"""
    help_table = Table(title="📚 Commands", box=ROUNDED, title_style="bold cyan")
    help_table.add_column("Command", style="bold yellow")
    help_table.add_column("Description", style="white")
    
    commands = [
        ("/help", "Show this help message"),
        ("/new [title]", "Start a new conversation"),
        ("/history", "Show conversation history"),
        ("/load <id>", "Load a previous conversation"),
        ("/delete <id>", "Delete a conversation"),
        ("/memory", "Show saved memories"),
        ("/remember <text>", "Save something to memory"),
        ("/forget <id>", "Delete a memory"),
        ("/search <query>", "Search the web"),
        ("/agent <task>", "Agent mode - AI uses tools autonomously"),
        ("/model [name]", "Switch AI model (dolphin-llama3, nous-hermes2, etc.)"),
        ("/knowledge add <text>", "Add to knowledge base"),
        ("/knowledge query <text>", "Search knowledge base"),
        ("/loadfile <path>", "Load file (PDF, TXT, etc.) into KB"),
        ("/run py <code>", "Run Python code (sandboxed)"),
        ("/run bash <cmd>", "Run Bash command (asks approval)"),
        ("/image <path>", "View image info & ASCII preview"),
        ("/describe <path>", "Describe image with AI vision (llava)"),
        ("/summarize", "Summarize current conversation"),
        ("/export [html|md|json]", "Export current chat"),
        ("/user [create|switch|list]", "User management"),
        ("/settings [key value]", "View/change settings"),
        ("/wipe [all|chats|memory]", "Wipe data"),
        ("/clear", "Clear the screen"),
        ("/exit", "Exit borgo-ai"),
    ]
    
    for cmd, desc in commands:
        help_table.add_row(cmd, desc)
    
    console.print(help_table)
    console.print("\n[dim]💡 Tip: Just type your message to chat with the AI![/dim]\n")


def print_user_message(message: str):
    """Print user message"""
    console.print(f"\n[bold blue]You:[/bold blue] {message}")


def print_assistant_start():
    """Print assistant message start"""
    console.print(f"\n[bold magenta]Borgo-AI:[/bold magenta] ", end="")


def print_streaming_token(token: str):
    """Print a streaming token"""
    console.print(token, end="", highlight=False)


def print_assistant_message(message: str, markdown: bool = True):
    """Print assistant message with optional markdown"""
    console.print(f"\n[bold magenta]Borgo-AI:[/bold magenta]")
    if markdown:
        # Rich's Markdown automatically handles code blocks with syntax highlighting
        console.print(Markdown(message, code_theme="monokai"))
    else:
        console.print(message)


def print_code_block(code: str, language: str = "python"):
    """Print a syntax-highlighted code block"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True, word_wrap=True)
    console.print(syntax)


def stream_assistant_response(tokens: Generator[str, None, None], markdown: bool = True) -> str:
    """Stream and print assistant response, return full text"""
    console.print(f"\n[bold magenta]Borgo-AI:[/bold magenta] ", end="")
    
    full_response = ""
    for token in tokens:
        full_response += token
        console.print(token, end="", highlight=False)
    
    console.print()  # Newline at end
    
    # Don't reprint - the streaming output is already shown
    # User can toggle markdown with /set markdown false if they prefer raw
    
    return full_response


def has_markdown(text: str) -> bool:
    """Check if text contains markdown formatting"""
    md_patterns = [
        r'^#{1,6}\s',  # Headers
        r'\*\*.*\*\*',  # Bold
        r'\*.*\*',      # Italic
        r'```',         # Code blocks
        r'`[^`]+`',     # Inline code
        r'^\s*[-*]\s',  # Lists
        r'^\s*\d+\.\s', # Numbered lists
        r'\[.*\]\(.*\)', # Links
    ]
    
    for pattern in md_patterns:
        if re.search(pattern, text, re.MULTILINE):
            return True
    return False


def print_thinking(message: str = "Thinking"):
    """Show thinking indicator"""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[dim]{message}...[/dim]"),
        transient=True,
    )


def print_error(message: str):
    """Print error message"""
    # Escape Rich markup characters to prevent crashes
    safe_message = str(message).replace("[", r"\[").replace("]", r"\]")
    console.print(f"\n[bold red]❌ Error:[/bold red] {safe_message}\n")


def print_success(message: str):
    """Print success message"""
    # Escape Rich markup characters
    safe_message = str(message).replace("[", r"\[").replace("]", r"\]")
    console.print(f"\n[bold green]✓[/bold green] {safe_message}\n")


def print_info(message: str):
    """Print info message"""
    # Escape Rich markup characters
    safe_message = message.replace("[", "\\[").replace("]", "\\]")
    console.print(f"\n[cyan]ℹ[/cyan] {safe_message}\n")


def print_warning(message: str):
    """Print warning message"""
    # Escape Rich markup characters
    safe_message = message.replace("[", "\\[").replace("]", "\\]")
    console.print(f"\n[yellow]⚠[/yellow] {safe_message}\n")


def print_conversations(conversations: list):
    """Print conversation list"""
    if not conversations:
        console.print("[dim]No conversations yet.[/dim]")
        return
    
    table = Table(title="💬 Conversations", box=ROUNDED)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Title", style="white")
    table.add_column("Messages", style="yellow", justify="right")
    table.add_column("Updated", style="dim")
    
    for conv in conversations:
        table.add_row(
            conv["id"],
            conv["title"][:40] + ("..." if len(conv["title"]) > 40 else ""),
            str(conv["messages"]),
            conv["updated"][:16]
        )
    
    console.print(table)


def print_memories(memories: list):
    """Print memories list"""
    if not memories:
        console.print("[dim]No memories saved yet.[/dim]")
        return
    
    table = Table(title="🧠 Memories", box=ROUNDED)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Content", style="white")
    table.add_column("Importance", style="yellow")
    table.add_column("Source", style="dim")
    
    for mem in memories[:20]:  # Limit display
        table.add_row(
            mem["memory_id"],
            mem["content"][:50] + ("..." if len(mem["content"]) > 50 else ""),
            f"{mem['importance']:.1f}",
            mem["source"]
        )
    
    console.print(table)


def print_settings(settings: dict):
    """Print settings"""
    table = Table(title="⚙️ Settings", box=ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    for key, value in settings.items():
        table.add_row(key, str(value))
    
    console.print(table)


def print_users(users: list, current: str):
    """Print user list"""
    table = Table(title="👥 Users", box=ROUNDED)
    table.add_column("Username", style="white")
    table.add_column("Status", style="cyan")
    
    for user in users:
        status = "✓ Active" if user == current else ""
        style = "bold green" if user == current else ""
        table.add_row(f"[{style}]{user}[/{style}]", status)
    
    console.print(table)


def print_stats(stats: dict):
    """Print user statistics"""
    table = Table(title="📊 Statistics", box=ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    table.add_row("Conversations", str(stats.get("conversations", 0)))
    table.add_row("Total Messages", str(stats.get("messages", 0)))
    table.add_row("Memories", str(stats.get("memories", 0)))
    table.add_row("Storage", f"{stats.get('storage_mb', 0)} MB")
    
    console.print(table)


def print_search_results(results: list):
    """Print search results"""
    if not results:
        console.print("[dim]No results found.[/dim]")
        return
    
    console.print("\n[bold cyan]🔍 Search Results:[/bold cyan]\n")
    
    for i, result in enumerate(results, 1):
        console.print(f"[bold]{i}. {result.title}[/bold]")
        console.print(f"   [dim]{result.url}[/dim]")
        console.print(f"   {result.snippet}\n")


def print_agent_step(step_type: str, content: str):
    """Print agent reasoning step"""
    icons = {
        "thought": "💭",
        "action": "⚡",
        "observation": "👁",
        "answer": "✅",
        "iteration": "🔄",
    }
    
    icon = icons.get(step_type, "•")
    
    if step_type == "thought":
        console.print(f"\n[dim]{icon} Thinking:[/dim] {content}")
    elif step_type == "action":
        console.print(f"\n[yellow]{icon} Action:[/yellow] {content}")
    elif step_type == "observation":
        console.print(f"\n[cyan]{icon} Observation:[/cyan] {content[:200]}{'...' if len(content) > 200 else ''}")
    elif step_type == "answer":
        console.print(f"\n[green]{icon} Final Answer:[/green]")
        console.print(Markdown(content))
    elif step_type == "iteration":
        console.print(f"\n[dim]─── Iteration {content} ───[/dim]")


def confirm(message: str) -> bool:
    """Ask for confirmation"""
    console.print(f"\n[yellow]{message} (y/n):[/yellow] ", end="")
    response = input().strip().lower()
    return response in ("y", "yes")


def prompt_input(prompt: str = "You") -> str:
    """Get user input with prompt"""
    try:
        console.print(f"\n[bold blue]{prompt}:[/bold blue] ", end="")
        return input()
    except EOFError:
        return "/exit"
    except KeyboardInterrupt:
        return "/exit"


def clear_screen():
    """Clear the screen"""
    console.clear()


def print_divider():
    """Print a divider line"""
    console.print("[dim]" + "─" * 60 + "[/dim]")


def print_code(code: str, language: str = "python"):
    """Print syntax-highlighted code"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def print_panel(content: str, title: str = "", style: str = "cyan"):
    """Print content in a panel"""
    console.print(Panel(content, title=title, border_style=style))
