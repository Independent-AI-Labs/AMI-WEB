#!/bin/bash

# MCP Server Start Script for AMI-WEB
# This script sets up and activates the conda environment before starting the MCP server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AMI-WEB MCP Server Launcher${NC}"
echo "================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Initialize conda for this shell session
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
elif [ -f /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh ]; then
    source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
elif [ -f /usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh ]; then
    source /usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh
else
    echo -e "${YELLOW}Warning: Could not find conda initialization script${NC}"
    echo "Trying to use conda from PATH..."
fi

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed or not in PATH${NC}"
    echo "Please install Miniconda or Anaconda first:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if 'web' environment exists
if conda env list | grep -q "^web "; then
    echo -e "${GREEN}Found existing 'web' conda environment${NC}"
else
    echo -e "${YELLOW}'web' environment not found. Creating it now...${NC}"
    
    # Create the environment with Python 3.12
    conda create -n web python=3.12 -y
    
    echo -e "${GREEN}Created 'web' conda environment${NC}"
fi

# Activate the environment
echo "Activating 'web' environment..."
conda activate web

# Check if requirements are installed
echo "Checking dependencies..."
if ! python -c "import selenium" 2>/dev/null; then
    echo -e "${YELLOW}Installing requirements...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}Dependencies already installed${NC}"
fi

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Check if Chrome is configured
if [ ! -f "config.yaml" ]; then
    echo -e "${YELLOW}Warning: config.yaml not found${NC}"
    echo "Using default configuration..."
fi

# Check for test flag
if [ "$1" = "--test" ] || [ "$1" = "--version" ]; then
    echo -e "${GREEN}Environment setup successful!${NC}"
    echo "Python version: $(python --version)"
    echo "Python path: $(which python)"
    echo "PYTHONPATH: $PYTHONPATH"
    exit 0
fi

# Start the MCP server
echo -e "${GREEN}Starting MCP server...${NC}"
echo "----------------------------------------"
exec python chrome_manager/mcp/mcp_stdio_server.py "$@"