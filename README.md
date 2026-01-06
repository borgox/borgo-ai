# 🤖 Borgo-AI
> the readme may or may not be made by borgo-ai
> **Local AI CLI Assistant powered by Llama 3.1**  
> Beautiful, fast, and fully private - runs entirely on your machine.

```
 ██████╗  ██████╗ ██████╗  ██████╗  ██████╗        █████╗ ██╗
 ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗      ██╔══██╗██║
 ██████╔╝██║   ██║██████╔╝██║  ███╗██║   ██║█████╗███████║██║
 ██╔══██╗██║   ██║██╔══██╗██║   ██║██║   ██║╚════╝██╔══██║██║
 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝      ██║  ██║██║
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝       ╚═╝  ╚═╝╚═╝
```

## ✨ Features

- 🦙 **Local LLM** - Powered by Llama 3.1:8b via Ollama (no API keys needed!)
- 🎨 **Beautiful CLI** - Rich terminal UI with ASCII art, markdown rendering, and themes
- 🔍 **Web Search** - AI-powered web browsing when it needs current information
- 🧠 **Memory System** - Remembers conversations and important facts
- 📚 **RAG Support** - Add documents to a knowledge base for context-aware responses  
- 🤖 **Agent Mode** - ReAct-style reasoning with tool use
- 👥 **Multi-User** - Per-user settings, memory, and conversation history
- 💾 **Persistent Storage** - Your chats and memories are saved locally
- ⚡ **Optimized** - Designed for RTX 3060 Ti (8GB VRAM) + 16GB RAM

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama** (if not already installed):
    ```bash
    sudo pacman -Syu
    sudo pacman -S ollama
    ```
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull the required models**:
   ```bash
   # Main LLM
   ollama pull llama3.1:8b
   
   # Embedding model
   ollama pull nomic-embed-text
   ```

3. **Start Ollama server**:
   ```bash
   ollama serve
   ```

### Installation

```bash
# Clone/navigate to the project
cd borgo-ai

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run Borgo-AI

```bash
# Interactive mode (recommended)
python main.py chat

# Or ask a single question
python main.py ask "What is the meaning of life?"

# With web search
python main.py ask "What's the latest news about AI?" --browse

# Agent mode
python main.py ask "Research the best Python web frameworks" --agent
```

## 📖 Commands

In interactive mode, use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/new` | Start a new conversation |
| `/history` | Show past conversations |
| `/load <id>` | Load a conversation |
| `/delete <id>` | Delete a conversation |
| `/memory` | Show saved memories |
| `/remember <text>` | Save to long-term memory |
| `/forget <id>` | Delete a memory |
| `/search <query>` | Search the web |
| `/agent <query>` | Use agent mode |
| `/knowledge add <text>` | Add to knowledge base |
| `/knowledge query <text>` | Search knowledge base |
| `/load <filepath>` | Load file into knowledge base |
| `/run <py\|bash> <code>` | Execute code (safe) |
| `/image <filepath>` | View image info |
| `/summarize [text]` | Summarize chat or text |
| `/export [html\|md\|json]` | Export conversation |
| `/user` | Manage users |
| `/settings` | View/change settings |
| `/wipe <all\|chats\|memory>` | Delete data |
| `/clear` | Clear screen |
| `/exit` | Exit borgo-ai |

## ⚙️ Settings

Customize your experience:

```bash
# In interactive mode:
/settings theme cyber        # cyber, minimal, or retro
/settings auto_browse true   # Auto-search when needed
/settings agentic_mode true  # Enable agent features
/settings markdown_enabled true
/settings stream_output true
/settings memory_enabled true
```

## 🏗️ Architecture

```
borgo-ai/
├── main.py          # CLI entry point
├── config.py        # Configuration settings
├── llm.py           # Ollama LLM integration
├── embeddings.py    # Vector embeddings + FAISS
├── browser.py       # Web search & scraping (GET only!)
├── rag.py           # Retrieval Augmented Generation
├── memory.py        # Conversation & long-term memory
├── user.py          # User management
├── agent.py         # Agentic AI capabilities (12 tools)
├── ui.py            # Rich terminal UI
├── files.py         # Document loading (PDF, DOCX, etc.)
├── executor.py      # Safe code execution
├── images.py        # Image viewing & info
├── summarizer.py    # Text summarization
├── export.py        # HTML/Markdown/JSON export
└── data/            # User data storage
    ├── users/       # Per-user data
    └── knowledge/   # RAG knowledge base
```

## 🎯 System Requirements

**Recommended:**
- GPU: RTX 3060 Ti or better (8GB+ VRAM)
- RAM: 16GB+
- Storage: 10GB for models

**Minimum:**
- GPU: Any CUDA-capable GPU with 6GB+ VRAM
- RAM: 12GB
- CPU-only mode works but is slower

## 🛠️ Hardware Optimization

The app is optimized for your RTX 3060 Ti:

- **Context window**: Limited to 8K tokens (vs 128K max) for memory efficiency
- **Embeddings**: Uses `nomic-embed-text` (768 dimensions) - fast and efficient
- **FAISS**: CPU version by default (GPU optional)
- **Streaming**: Token-by-token output for better UX

## 📝 Examples

### Basic Chat
```
You: What's the best way to learn Python?

Borgo-AI: Here are my top recommendations for learning Python...
```

### Web Search
```
/search latest AI developments 2024
```

### Agent Mode
```
/agent Find the current price of Bitcoin and compare it to last month
```

### Knowledge Base
```
# Add documentation
/knowledge add Python's GIL (Global Interpreter Lock) prevents multiple native threads from executing Python bytecodes at once...

# Later, ask about it
You: What is Python's GIL?
# The AI will use your added knowledge!
```

### Memory
```
/remember My favorite programming language is Rust
/remember I'm working on a web scraping project

# Later...
You: What project am I working on?
Borgo-AI: Based on my memories, you're working on a web scraping project!
```

## 🔒 Privacy

- **100% Local**: No data leaves your machine
- **No API Keys**: Powered by Ollama, completely free
- **Your Data**: All conversations and memories stored locally in `./data`

## 🐛 Troubleshooting

**"Cannot connect to Ollama"**
```bash
# Make sure Ollama is running
ollama serve
```

**"Model not found"**
```bash
# Pull the required models
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

**Out of memory**
- Reduce `context_window` in `config.py`
- Use a smaller model: `ollama pull llama3.1:7b`

**Slow responses**
- Ensure GPU is being used: `nvidia-smi`
- Check Ollama is using GPU: model loads should mention CUDA

## 📜 License

MIT License - feel free to modify and use as you wish!

---

**Made with ❤️ for local AI enthusiasts**
