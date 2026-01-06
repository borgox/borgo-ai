"""
Export Module - Export conversations to HTML and other formats
"""
import json
import html
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import re

from .config import USERS_DIR


class HTMLExporter:
    """Export conversations to beautiful HTML"""
    
    CSS_STYLES = """
    <style>
        :root {
            --bg-color: #1a1b26;
            --surface-color: #24283b;
            --text-color: #c0caf5;
            --text-muted: #565f89;
            --user-color: #7aa2f7;
            --assistant-color: #bb9af7;
            --accent-color: #7dcfff;
            --code-bg: #1f2335;
            --border-color: #3b4261;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            text-align: center;
            padding: 2rem 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }
        
        .header h1 {
            color: var(--accent-color);
            font-size: 2.5rem;
            margin: 0;
            letter-spacing: -0.02em;
        }
        
        .header .logo {
            font-family: monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
            white-space: pre;
        }
        
        .meta {
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        .conversation {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .message {
            display: flex;
            flex-direction: column;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
        }
        
        .message.user {
            border-left: 4px solid var(--user-color);
        }
        
        .message.assistant {
            border-left: 4px solid var(--assistant-color);
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .message-role {
            font-weight: 600;
            font-size: 0.9rem;
        }
        
        .message.user .message-role {
            color: var(--user-color);
        }
        
        .message.assistant .message-role {
            color: var(--assistant-color);
        }
        
        .message-time {
            color: var(--text-muted);
            font-size: 0.75rem;
        }
        
        .message-content {
            color: var(--text-color);
        }
        
        .message-content p {
            margin: 0 0 1rem 0;
        }
        
        .message-content p:last-child {
            margin-bottom: 0;
        }
        
        .message-content code {
            background-color: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.9em;
        }
        
        .message-content pre {
            background-color: var(--code-bg);
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
        }
        
        .message-content pre code {
            background: none;
            padding: 0;
        }
        
        .message-content ul, .message-content ol {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
        }
        
        .message-content li {
            margin: 0.25rem 0;
        }
        
        .message-content h1, .message-content h2, .message-content h3 {
            color: var(--accent-color);
            margin: 1rem 0 0.5rem 0;
        }
        
        .message-content blockquote {
            border-left: 3px solid var(--accent-color);
            margin: 1rem 0;
            padding-left: 1rem;
            color: var(--text-muted);
        }
        
        .message-content a {
            color: var(--accent-color);
            text-decoration: none;
        }
        
        .message-content a:hover {
            text-decoration: underline;
        }
        
        .footer {
            text-align: center;
            padding: 2rem 0;
            margin-top: 2rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.85rem;
        }
        
        @media (max-width: 600px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
            
            .message {
                padding: 0.75rem 1rem;
            }
        }
        
        /* Syntax highlighting */
        .hljs-keyword { color: #bb9af7; }
        .hljs-string { color: #9ece6a; }
        .hljs-number { color: #ff9e64; }
        .hljs-comment { color: #565f89; font-style: italic; }
        .hljs-function { color: #7aa2f7; }
        .hljs-class { color: #7dcfff; }
    </style>
    """
    
    LOGO = """
 ██████╗  ██████╗ ██████╗  ██████╗  ██████╗        █████╗ ██╗
 ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗      ██╔══██╗██║
 ██████╔╝██║   ██║██████╔╝██║  ███╗██║   ██║█████╗███████║██║
 ██╔══██╗██║   ██║██╔══██╗██║   ██║██║   ██║╚════╝██╔══██║██║
 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝      ██║  ██║██║
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝       ╚═╝  ╚═╝╚═╝"""
    
    def __init__(self):
        pass
    
    def markdown_to_html(self, text: str) -> str:
        """Convert markdown to HTML"""
        # Escape HTML first
        text = html.escape(text)
        
        # Code blocks (``` ... ```)
        text = re.sub(
            r'```(\w+)?\n(.*?)```',
            lambda m: f'<pre><code class="language-{m.group(1) or "text"}">{m.group(2)}</code></pre>',
            text,
            flags=re.DOTALL
        )
        
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Lists (simple)
        text = re.sub(r'^[\-\*] (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text)
        
        # Blockquotes
        text = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
        
        # Paragraphs (double newlines)
        paragraphs = text.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            processed.append(p)
        text = '\n'.join(processed)
        
        # Single newlines to <br> within paragraphs
        text = re.sub(r'(?<!</p>)\n(?!<)', '<br>\n', text)
        
        return text
    
    def export_conversation(
        self,
        messages: List[Dict],
        title: str = "Conversation",
        username: str = "User",
        export_path: Optional[str] = None
    ) -> str:
        """Export a conversation to HTML"""
        
        now = datetime.now()
        
        # Build messages HTML
        messages_html = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            role_display = username if role == "user" else "Borgo-AI"
            content_html = self.markdown_to_html(content)
            
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M")
                except:
                    pass
            
            messages_html += f"""
            <div class="message {role}">
                <div class="message-header">
                    <span class="message-role">{role_display}</span>
                    <span class="message-time">{time_str}</span>
                </div>
                <div class="message-content">
                    {content_html}
                </div>
            </div>
            """
        
        # Build full HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Borgo-AI</title>
    {self.CSS_STYLES}
</head>
<body>
    <div class="container">
        <header class="header">
            <pre class="logo">{html.escape(self.LOGO)}</pre>
            <h1>{html.escape(title)}</h1>
            <p class="meta">
                Exported on {now.strftime("%B %d, %Y at %H:%M")}
                • {len(messages)} messages
            </p>
        </header>
        
        <main class="conversation">
            {messages_html}
        </main>
        
        <footer class="footer">
            <p>Generated by Borgo-AI • Local AI Assistant</p>
            <p>Powered by Llama 3.1</p>
        </footer>
    </div>
</body>
</html>"""
        
        # Save if path provided
        if export_path:
            Path(export_path).write_text(html_content, encoding='utf-8')
        
        return html_content
    
    def export_all_conversations(
        self,
        username: str,
        output_dir: str
    ) -> List[str]:
        """Export all conversations for a user"""
        from .memory import get_memory_manager
        
        mm = get_memory_manager(username)
        conversations = mm.list_conversations()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported = []
        
        for conv_info in conversations:
            conv = mm.get_conversation(conv_info["id"])
            if conv:
                messages = [m.to_dict() for m in conv.messages]
                filename = f"conversation_{conv.conversation_id}_{conv.title[:30]}.html"
                filename = re.sub(r'[^\w\-.]', '_', filename)
                filepath = output_path / filename
                
                self.export_conversation(
                    messages=messages,
                    title=conv.title,
                    username=username,
                    export_path=str(filepath)
                )
                exported.append(str(filepath))
        
        return exported


class MarkdownExporter:
    """Export conversations to Markdown"""
    
    def export_conversation(
        self,
        messages: List[Dict],
        title: str = "Conversation",
        username: str = "User",
        export_path: Optional[str] = None
    ) -> str:
        """Export a conversation to Markdown"""
        
        now = datetime.now()
        
        md_content = f"""# {title}

*Exported from Borgo-AI on {now.strftime("%B %d, %Y at %H:%M")}*

---

"""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            role_display = username if role == "user" else "🤖 Borgo-AI"
            
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = f" *({dt.strftime('%H:%M')})*"
                except:
                    pass
            
            md_content += f"### {role_display}{time_str}\n\n{content}\n\n---\n\n"
        
        md_content += "\n*Generated by Borgo-AI - Local AI Assistant*\n"
        
        if export_path:
            Path(export_path).write_text(md_content, encoding='utf-8')
        
        return md_content


class JSONExporter:
    """Export conversations to JSON"""
    
    def export_conversation(
        self,
        messages: List[Dict],
        title: str = "Conversation",
        username: str = "User",
        export_path: Optional[str] = None
    ) -> str:
        """Export a conversation to JSON"""
        
        data = {
            "title": title,
            "username": username,
            "exported_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": messages
        }
        
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        
        if export_path:
            Path(export_path).write_text(json_content, encoding='utf-8')
        
        return json_content


# Convenience functions
def export_to_html(
    messages: List[Dict],
    title: str = "Conversation",
    username: str = "User",
    filepath: Optional[str] = None
) -> str:
    """Export conversation to HTML"""
    exporter = HTMLExporter()
    return exporter.export_conversation(messages, title, username, filepath)


def export_to_markdown(
    messages: List[Dict],
    title: str = "Conversation",
    username: str = "User",
    filepath: Optional[str] = None
) -> str:
    """Export conversation to Markdown"""
    exporter = MarkdownExporter()
    return exporter.export_conversation(messages, title, username, filepath)


def export_to_json(
    messages: List[Dict],
    title: str = "Conversation",
    username: str = "User",
    filepath: Optional[str] = None
) -> str:
    """Export conversation to JSON"""
    exporter = JSONExporter()
    return exporter.export_conversation(messages, title, username, filepath)
