# 🤖 Borgo-AI
> the readme may or may not be made by borgo-ai
> **Local AI CLI Assistant powered by Various LLMs**  
> Beautiful, fast, and fully private - runs entirely on your machine.
> This project is NOT complete and you may find bugs all around. Either report them or fork the repo and fix them :)
```
 ██████╗  ██████╗ ██████╗  ██████╗  ██████╗        █████╗ ██╗
 ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗      ██╔══██╗██║
 ██████╔╝██║   ██║██████╔╝██║  ███╗██║   ██║█████╗███████║██║
 ██╔══██╗██║   ██║██╔══██╗██║   ██║██║   ██║╚════╝██╔══██║██║
 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝      ██║  ██║██║
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝       ╚═╝  ╚═╝╚═╝
```

## ✨ Features

- 🦙 **Local LLM** - Powered by Ollama (default: dolphin-llama3:8b). Supports 8+ models including uncensored variants
- 🎨 **Beautiful CLI** - Rich terminal UI with ASCII art, markdown rendering, and 3 themes (cyber/minimal/retro)
- 🔍 **Web Search** - Integrated Google search with AI-powered browsing
- 🧠 **Memory System** - Dual memory: short-term conversation history + long-term semantic memory with FAISS
- 📚 **RAG Support** - Knowledge base with semantic search. Load PDFs, DOCX, TXT files
- 🤖 **Agent Mode** - ReAct-style reasoning with 14+ tools (search, bash, python, files, images)
- 👥 **Multi-User** - Per-user profiles with isolated settings, memory, and conversation history
- 💾 **Persistent Storage** - All data saved locally in JSON + FAISS indexes
- 🖼️ **Image Support** - View images, get info, AI descriptions with llava vision model
- 📝 **Summarization** - Automatic conversation and text summarization with key point extraction
- 🐍 **Code Execution** - Safe sandboxed Python + bash command execution with user confirmation
- 📤 **Export** - Export conversations to HTML, Markdown, or JSON formats
- ⚡ **Optimized** - Designed for RTX 3060 Ti (8GB VRAM) + 16GB RAM but works on any system

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
   # Main LLM (default)
   ollama pull dolphin-llama3:8b
   
   # Embedding model
   ollama pull nomic-embed-text
   
   # Optional: Vision model for image descriptions
   ollama pull llava
   ```

3. **Start Ollama server**:
   ```bash
   ollama serve
   ```

### Installation

```bash
# Clone/navigate to the project
cd borgo-ai

# Install globally (recommended)
pip install .

# Or for development
pip install -e .
```

### Run Borgo-AI

After installation, you can use the `borgo-ai` command from anywhere:

```bash
# Interactive mode (recommended)
borgo-ai chat

# Or ask a single question
borgo-ai ask "What is the meaning of life?"

# With web search
borgo-ai ask "What's the latest news about AI?" --browse

# Agent mode
borgo-ai ask "Research the best Python web frameworks" --agent

# For local development (if not installed)
python borgo-ai.py chat
```

## 📖 CLI Commands

The `borgo-ai` command provides several subcommands:

```bash
borgo-ai chat              # Start interactive chat mode
borgo-ai ask <question>    # Ask a single question
borgo-ai search <query>    # Search the web
borgo-ai users             # List and manage users
borgo-ai settings          # Show current settings
borgo-ai version           # Show version info
```

## 📖 Interactive Commands

In interactive mode, use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/new [title]` | Start a new conversation |
| `/history` | Show past conversations |
| `/load <id>` | Load a conversation |
| `/delete <id>` | Delete a conversation |
| `/memory` | Show saved memories |
| `/remember <text>` | Save to long-term memory |
| `/forget <id>` | Delete a memory |
| `/search <query>` | Search the web |
| `/agent <query>` | Use full agent mode for complex tasks |
| `/knowledge add <text>` | Add to knowledge base |
| `/knowledge query <text>` | Search knowledge base |
| `/knowledge clear` | Clear entire knowledge base |
| `/loadfile <filepath>` | Load file (PDF/DOCX/TXT) into knowledge base |
| `/run <py\|bash> <code>` | Execute code (sandboxed) |
| `/image <filepath>` | View image info + ASCII preview |
| `/describe <filepath>` | AI image description (requires llava) |
| `/summarize [text]` | Summarize conversation or text |
| `/export [html\|md\|json\|all]` | Export conversation or all data |
| `/user [create\|switch\|delete]` | Manage users |
| `/settings [key] [value]` | View/change settings |
| `/model [name]` | Switch LLM model or show available models |
| `/stats` | Show usage statistics |
| `/wipe <all\|chats\|memory>` | Delete data (with confirmation) |
| `/clear` | Clear screen |
| `/exit` `/quit` `/q` | Exit borgo-ai |

## 🤖 Available Models

Borgo-AI supports multiple LLM models. Switch anytime with `/model` command:

**Uncensored Models (Recommended for Freedom):**
- `dolphin-llama3:8b` - **Default**, best all-rounder, mostly uncensored (~5GB VRAM)
- `wizard-vicuna-uncensored:13b` - Truly uncensored, no limits (~8GB VRAM)
- `dolphin-mistral:7b-v2.6` - Uncensored + great coder (~5GB VRAM)
- `dolphin-phi:2.7b` - Small & fast, uncensored (~2GB VRAM)

**Standard Models:**
- `nous-hermes2:10.7b` - Powerful for complex tasks (~7GB VRAM)
- `llama3.1:8b` - Official Meta model, censored (~5GB VRAM)
- `deepseek-coder:6.7b` - Specialized for coding (~5GB VRAM)
- `llava` - Vision model for image description (~5GB VRAM)

**Quick Switch:**
```bash
/model wizard     # Switch to wizard-vicuna-uncensored
/model hermes     # Switch to nous-hermes2
/model coder      # Switch to deepseek-coder
/model            # Show all available models and aliases
```

## ⚙️ Settings

Customize your experience:

```bash
# View current settings
/settings

# Change settings (in interactive mode):
/settings theme cyber              # Theme: cyber, minimal, or retro
/settings auto_browse true         # Auto web search when AI needs it
/settings agentic_mode true        # Enable full agent mode by default
/settings markdown_enabled true    # Render markdown in responses
/settings stream_output true       # Stream tokens as they're generated
/settings memory_enabled true      # Use long-term memory
/settings show_thinking true       # Show "thinking" animations
```

**Available Settings:**
- `theme` - UI theme (cyber/minimal/retro)
- `show_thinking` - Show loading/thinking animations (bool)
- `auto_browse` - Automatically search web when needed (bool)
- `agentic_mode` - Enable agent mode by default (bool)
- `markdown_enabled` - Render markdown in responses (bool)
- `stream_output` - Stream output token-by-token (bool)
- `memory_enabled` - Use semantic memory system (bool)

## 🏗️ Architecture

```
borgo-ai/
├── src/
│   └── borgo_ai/                # Main package
│       ├── __init__.py          # Package init
│       ├── main.py              # CLI entry point with Typer
│       ├── config.py            # Configuration (LLM, embeddings, memory, etc.)
│       ├── llm.py               # Ollama LLM integration
│       ├── embeddings.py        # Vector embeddings + FAISS
│       ├── browser.py           # Web search & scraping
│       ├── rag.py               # Retrieval Augmented Generation
│       ├── memory.py            # Conversation & long-term memory
│       ├── user.py              # Multi-user management
│       ├── agent.py             # Agentic AI with 14+ tools
│       ├── ui.py                # Rich terminal UI (themes, formatting)
│       ├── files.py             # Document loading (PDF, DOCX, TXT)
│       ├── executor.py          # Sandboxed code execution
│       ├── images.py            # Image viewing, ASCII art, AI vision
│       ├── summarizer.py        # Text/conversation summarization
│       └── export.py            # HTML/Markdown/JSON export
├── tests/                       # Unit tests
│   └── test_basic.py            # Basic import and config tests
├── data/                        # User data storage (auto-created)
│   ├── users/                   # Per-user profiles
│   │   ├── default/             # Default user
│   │   │   ├── conversations.json
│   │   │   ├── memories.json
│   │   │   ├── settings.json
│   │   │   └── memory_index/    # FAISS index
│   │   └── [username]/          # Additional users
│   └── knowledge/               # Global RAG knowledge base
│       └── default/
│           └── index.faiss
├── borgo-ai.py          # Local runner script (development)
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
├── README.md            # This file
├── requirements.txt     # Python dependencies (pinned versions)
├── setup.py             # Package setup with entry points
└── setup.sh             # Cross-platform setup script
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

### Check Version
```bash
borgo-ai version
# Output:
# Borgo-AI v0.1.0
# 
# Local AI Assistant powered by various LLMs
# Optimized for RTX 3060 Ti + 16GB RAM
# 
# Components:
# • LLM: dolphin-llama3:8b (switchable)
# • Embeddings: nomic-embed-text
# • Vector Store: FAISS
# • Memory: Persistent conversation + long-term semantic memory
# • RAG: Knowledge base with semantic search
# • Agent: ReAct-style reasoning with 14+ tools
```

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
```bash
# Add documentation
/knowledge add "Python's GIL (Global Interpreter Lock) prevents multiple native threads from executing Python bytecodes at once..."

# Load a file into knowledge base
/loadfile /path/to/document.pdf

# Query knowledge base
/knowledge query "What is the GIL?"

# Later, ask naturally - the AI will use your knowledge base!
You: What is Python's GIL?
Borgo-AI: [retrieves from knowledge base and explains]
```

### Memory System
```bash
# Save important facts
/remember My favorite programming language is Rust
/remember I'm working on a web scraping project for crypto data

# View all memories
/memory

# Later, the AI remembers automatically
You: What project am I working on?
Borgo-AI: Based on my memories, you're working on a web scraping project for crypto data!
```

### Code Execution
```bash
# Execute Python code
/run python print("Hello, World!")

# Execute bash commands (with confirmation)
/run bash df -h
```

### Image Analysis
```bash
# View image info
/image photo.jpg

# AI description with vision model
/describe photo.jpg
```

### Model Switching
```bash
# Show available models
/model

# Switch to different model
/model wizard-vicuna-uncensored:13b
/model hermes
/model coder
```

## 🔒 Privacy & Security

- **100% Local**: All processing happens on your machine - no data ever leaves
- **No API Keys Required**: Powered by Ollama, completely free and open source
- **Your Data, Your Control**: All conversations and memories stored locally in `./data`
- **No Telemetry**: Zero tracking, analytics, or phone-home features
- **Sandboxed Execution**: Code execution is sandboxed with safety checks
- **User Confirmation**: Bash commands require explicit user approval

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=borgo_ai
```

**Current Tests:**
- Import validation for all modules
- Configuration loading
- Data directory creation
- Basic functionality checks

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest tests/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

**Areas for Contribution:**
- Additional LLM provider support (OpenAI, Anthropic, local alternatives)
- More document formats (Excel, PowerPoint, etc.)
- Enhanced agent tools
- UI improvements and themes
- Better error handling
- Performance optimizations
- Documentation improvements

## 📦 Dependencies

**Core:**
- `typer[all]>=0.9.0` - Modern CLI framework with rich support
- `rich>=13.0.0` - Beautiful terminal formatting
- `requests>=2.31.0` - HTTP client for Ollama and web scraping

**AI/ML:**
- `faiss-cpu>=1.7.4` - Vector similarity search (CPU version)
- `numpy>=1.24.0` - Numerical computing

**Document Processing:**
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - XML/HTML processing
- `pypdf>=3.0.0` - PDF reading
- `python-docx>=0.8.11` - Word document reading
- `chardet>=5.0.0` - Character encoding detection

**Image Processing:**
- `Pillow>=10.0.0` - Image manipulation and ASCII art

## 🚀 Roadmap

**Planned Features:**
- [ ] Plugin system for custom tools
- [ ] Voice input/output support
- [ ] Web UI alternative to CLI
- [ ] Docker containerization
- [ ] Cloud sync (optional, encrypted)
- [ ] More LLM providers (OpenAI, Anthropic)
- [ ] Improved summarization algorithms
- [ ] Better context management
- [ ] Multi-language support

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama** - For making local LLMs accessible
- **Meta AI** - For Llama models
- **Eric Hartford** - For Dolphin fine-tunes
- **Rich** - For beautiful terminal output
- **Typer** - For elegant CLI development

---

**Made with ❤️ by borgo-ai**


> P.S: This is just a fun project, also made with the help of ai but not entirely, just for small things. I made this to learn mroe about AI 