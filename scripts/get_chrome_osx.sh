#!/bin/bash
# Script to download and setup Chrome and ChromeDriver for macOS
# Downloads Chrome for Testing (stable channel) and matching ChromeDriver

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build"

echo -e "${GREEN}Chrome and ChromeDriver Setup for macOS${NC}"
echo "Project root: ${PROJECT_ROOT}"
echo "Build directory: ${BUILD_DIR}"

# Create build directory if it doesn't exist
mkdir -p "${BUILD_DIR}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
if ! command_exists curl; then
    echo -e "${RED}Error: curl is required but not installed${NC}"
    exit 1
fi

if ! command_exists unzip; then
    echo -e "${RED}Error: unzip is required but not installed${NC}"
    exit 1
fi

# Function to get the latest Chrome 141+ version
get_latest_chrome_version() {
    echo -e "${YELLOW}Fetching latest Chrome versions...${NC}" >&2
    local version_url="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    
    # Get the Dev channel version (141+)
    local version=$(curl -s "$version_url" | python3 -c "
import json
import sys
data = json.load(sys.stdin)
# Get Dev channel for Chrome 141+
if 'Dev' in data.get('channels', {}):
    version = data['channels']['Dev']['version']
    print(version)
else:
    # Fallback to a known Chrome 141 version
    print('141.0.7367.0')
" 2>/dev/null)
    
    if [ -z "$version" ]; then
        # If that fails, use a known Chrome 141 version
        echo -e "${YELLOW}Using known Chrome 141 version...${NC}" >&2
        version="141.0.7367.0"
    fi
    
    echo "$version"
}

# Function to download Chrome
download_chrome() {
    local version=$1
    local chrome_dir="${BUILD_DIR}/chrome-mac-${version}"
    local chrome_zip="${BUILD_DIR}/chrome-mac-${version}.zip"
    
    # Check if already downloaded
    if [ -d "$chrome_dir" ]; then
        echo -e "${GREEN}Chrome ${version} already exists at ${chrome_dir}${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Downloading Chrome ${version} for macOS...${NC}"
    
    # Determine architecture
    local arch="x64"
    if [[ $(uname -m) == "arm64" ]]; then
        arch="arm64"
    fi
    
    # Download URL for Chrome
    local chrome_url="https://storage.googleapis.com/chrome-for-testing-public/${version}/mac-${arch}/chrome-mac-${arch}.zip"
    
    echo "Downloading from: ${chrome_url}"
    
    if ! curl -L -o "$chrome_zip" "$chrome_url"; then
        echo -e "${RED}Failed to download Chrome${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Extracting Chrome...${NC}"
    unzip -q -o "$chrome_zip" -d "${BUILD_DIR}"
    
    # Rename extracted folder
    if [ -d "${BUILD_DIR}/chrome-mac-${arch}" ]; then
        mv "${BUILD_DIR}/chrome-mac-${arch}" "$chrome_dir"
    fi
    
    # Clean up zip file
    rm -f "$chrome_zip"
    
    # Remove quarantine attribute on macOS
    if command_exists xattr; then
        echo -e "${YELLOW}Removing quarantine attributes...${NC}"
        xattr -cr "$chrome_dir" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}Chrome ${version} downloaded to ${chrome_dir}${NC}"
}

# Function to download ChromeDriver
download_chromedriver() {
    local version=$1
    local driver_dir="${BUILD_DIR}"
    local driver_zip="${BUILD_DIR}/chromedriver-mac-${version}.zip"
    local driver_path="${driver_dir}/chromedriver"
    
    # Check if already downloaded
    if [ -f "$driver_path" ]; then
        # Check version
        if "$driver_path" --version 2>/dev/null | grep -q "$version"; then
            echo -e "${GREEN}ChromeDriver ${version} already exists at ${driver_path}${NC}"
            return 0
        else
            echo -e "${YELLOW}ChromeDriver exists but version mismatch. Updating...${NC}"
            rm -f "$driver_path"
        fi
    fi
    
    echo -e "${YELLOW}Downloading ChromeDriver ${version} for macOS...${NC}"
    
    # Determine architecture
    local arch="x64"
    if [[ $(uname -m) == "arm64" ]]; then
        arch="arm64"
    fi
    
    # Download URL for ChromeDriver
    local driver_url="https://storage.googleapis.com/chrome-for-testing-public/${version}/mac-${arch}/chromedriver-mac-${arch}.zip"
    
    echo "Downloading from: ${driver_url}"
    
    if ! curl -L -o "$driver_zip" "$driver_url"; then
        echo -e "${RED}Failed to download ChromeDriver${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Extracting ChromeDriver...${NC}"
    unzip -q -o "$driver_zip" -d "${BUILD_DIR}/temp_chromedriver"
    
    # Move ChromeDriver to build directory
    if [ -f "${BUILD_DIR}/temp_chromedriver/chromedriver-mac-${arch}/chromedriver" ]; then
        mv "${BUILD_DIR}/temp_chromedriver/chromedriver-mac-${arch}/chromedriver" "$driver_path"
    fi
    
    # Clean up
    rm -rf "${BUILD_DIR}/temp_chromedriver"
    rm -f "$driver_zip"
    
    # Make ChromeDriver executable
    chmod +x "$driver_path"
    
    # Remove quarantine attribute on macOS
    if command_exists xattr; then
        echo -e "${YELLOW}Removing quarantine attributes from ChromeDriver...${NC}"
        xattr -cr "$driver_path" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}ChromeDriver ${version} downloaded to ${driver_path}${NC}"
}

# Function to create/update config.yaml
update_config() {
    local version=$1
    local config_file="${PROJECT_ROOT}/config.yaml"
    local config_sample="${PROJECT_ROOT}/config.sample.yaml"
    local chrome_path="./build/chrome-mac-${version}/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    local driver_path="./build/chromedriver"
    
    # If config.yaml doesn't exist, copy from sample
    if [ ! -f "$config_file" ] && [ -f "$config_sample" ]; then
        echo -e "${YELLOW}Creating config.yaml from config.sample.yaml...${NC}"
        cp "$config_sample" "$config_file"
    fi
    
    # Update paths in config.yaml if it exists
    if [ -f "$config_file" ]; then
        echo -e "${YELLOW}Updating config.yaml with macOS paths...${NC}"
        
        # Use sed to update the paths in the config file
        # First, escape forward slashes in the paths for sed
        escaped_chrome_path=$(echo "$chrome_path" | sed 's/\//\\\//g')
        escaped_driver_path=$(echo "$driver_path" | sed 's/\//\\\//g')
        
        # Update chrome_binary_path
        if grep -q "chrome_binary_path:" "$config_file"; then
            sed -i '' "s/chrome_binary_path:.*/chrome_binary_path: \"${escaped_chrome_path}\"/" "$config_file"
        else
            echo "    chrome_binary_path: \"${chrome_path}\"" >> "$config_file"
        fi
        
        # Update chromedriver_path
        if grep -q "chromedriver_path:" "$config_file"; then
            sed -i '' "s/chromedriver_path:.*/chromedriver_path: \"${escaped_driver_path}\"/" "$config_file"
        else
            echo "    chromedriver_path: \"${driver_path}\"" >> "$config_file"
        fi
        
        echo -e "${GREEN}Config file updated with macOS paths${NC}"
    else
        echo -e "${YELLOW}Warning: config.yaml not found. Please create it from config.sample.yaml${NC}"
        echo -e "${YELLOW}Chrome binary: ${chrome_path}${NC}"
        echo -e "${YELLOW}ChromeDriver: ${driver_path}${NC}"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}Starting Chrome and ChromeDriver setup...${NC}"
    
    # Get the latest Chrome version (141+)
    CHROME_VERSION=$(get_latest_chrome_version)
    echo -e "${GREEN}Chrome version selected: ${CHROME_VERSION}${NC}"
    
    # Check if version is 141 or higher
    MAJOR_VERSION=$(echo "$CHROME_VERSION" | cut -d. -f1)
    if [ "$MAJOR_VERSION" -ge 141 ]; then
        echo -e "${GREEN}✓ Chrome version ${CHROME_VERSION} meets the requirement (141+)${NC}"
    else
        echo -e "${YELLOW}Warning: Chrome version ${CHROME_VERSION} is older than 141${NC}"
    fi
    
    # Download Chrome
    download_chrome "$CHROME_VERSION"
    
    # Download ChromeDriver
    download_chromedriver "$CHROME_VERSION"
    
    # Update config
    update_config "$CHROME_VERSION"
    
    # Verify installation
    echo -e "\n${GREEN}Verification:${NC}"
    
    # Check Chrome
    CHROME_BINARY="${BUILD_DIR}/chrome-mac-${CHROME_VERSION}/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    if [ -f "$CHROME_BINARY" ]; then
        CHROME_ACTUAL_VERSION=$("$CHROME_BINARY" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        echo -e "${GREEN}✓ Chrome installed: ${CHROME_ACTUAL_VERSION}${NC}"
    else
        echo -e "${RED}✗ Chrome binary not found${NC}"
    fi
    
    # Check ChromeDriver
    DRIVER_BINARY="${BUILD_DIR}/chromedriver"
    if [ -f "$DRIVER_BINARY" ]; then
        DRIVER_VERSION=$("$DRIVER_BINARY" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        echo -e "${GREEN}✓ ChromeDriver installed: ${DRIVER_VERSION}${NC}"
    else
        echo -e "${RED}✗ ChromeDriver not found${NC}"
    fi
    
    echo -e "\n${GREEN}Setup complete!${NC}"
    echo -e "${YELLOW}Note: If you encounter 'Operation not permitted' errors, you may need to:${NC}"
    echo -e "${YELLOW}1. Go to System Settings > Privacy & Security${NC}"
    echo -e "${YELLOW}2. Allow the Chrome and ChromeDriver binaries to run${NC}"
}

# Run main function
main