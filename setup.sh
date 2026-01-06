#!/bin/bash
# Borgo-AI Setup Script

set -e

echo "
 ██████╗  ██████╗ ██████╗  ██████╗  ██████╗        █████╗ ██╗
 ██╔══██╗██╔═══██╗██╔══██╗██╔════╝ ██╔═══██╗      ██╔══██╗██║
 ██████╔╝██║   ██║██████╔╝██║  ███╗██║   ██║█████╗███████║██║
 ██╔══██╗██║   ██║██╔══██╗██║   ██║██║   ██║╚════╝██╔══██║██║
 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝      ██║  ██║██║
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝       ╚═╝  ╚═╝╚═╝

              🚀 Setup Script
"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for Python
echo -e "${YELLOW}Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Python not found! Please install Python 3.8+${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found $($PYTHON --version)${NC}"

# Check for Ollama
echo -e "\n${YELLOW}Checking Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama is installed${NC}"
else
    echo -e "${YELLOW}Ollama not found. Installing...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
    echo -e "${GREEN}✓ Ollama installed${NC}"
fi

# Create virtual environment
echo -e "\n${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate and install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Pull Ollama models
echo -e "\n${YELLOW}Pulling AI models (this may take a while)...${NC}"

# Check if ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Starting Ollama server...${NC}"
    ollama serve &
    sleep 3
fi

echo -e "${YELLOW}Pulling llama3.1:8b (main model ~4.7GB)...${NC}"
ollama pull llama3.1:8b

echo -e "${YELLOW}Pulling nomic-embed-text (embeddings ~274MB)...${NC}"
ollama pull nomic-embed-text

echo -e "${GREEN}✓ Models ready${NC}"

# Create data directories
mkdir -p data/users data/knowledge

echo -e "
${GREEN}════════════════════════════════════════════════════════════════
  ✅ Setup Complete!
════════════════════════════════════════════════════════════════${NC}

To run Borgo-AI:

  1. Activate the virtual environment:
     ${YELLOW}source venv/bin/activate${NC}

  2. Make sure Ollama is running:
     ${YELLOW}ollama serve${NC}

  3. Start Borgo-AI:
     ${YELLOW}python main.py chat${NC}

Enjoy your local AI assistant! 🤖
"
