#!/bin/bash
set -e  # Exit immediately on error
set -o pipefail  # Capture pipe command failures

# Function to display colored messages
status_msg() {
    echo -e "\e[1;32m>>> $1\e[0m"
}

error_msg() {
    echo -e "\e[1;31m!!! ERROR: $1\e[0m"
    exit 1
}

# Install dependencies
install_dependencies() {
    status_msg "Installing system dependencies"
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
        wget \
        tar \
        curl \
        net-tools \
        iputils-ping > /dev/null
}

# Download and setup wrapper
setup_wrapper() {
    status_msg "Detecting system architecture"
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "x86_64" ]; then
        WRAPPER_URL="https://github.com/zhaarey/wrapper/releases/download/linux.V2/wrapper.x86_64.tar.gz"
    elif [ "$ARCH" = "aarch64" ]; then
        WRAPPER_URL="https://github.com/zhaarey/wrapper/releases/download/arm64/wrapper.arm64.tar.gz"
    else
        error_msg "Unsupported architecture: $ARCH"
    fi

    status_msg "Downloading wrapper for $ARCH"
    mkdir -p /app/wrapper
    cd /app/wrapper
    wget -q "$WRAPPER_URL" -O wrapper.tar.gz
    
    status_msg "Extracting wrapper package"
    tar -xzf wrapper.tar.gz
    rm wrapper.tar.gz
    chmod +x wrapper
}

# Configure environment
configure_environment() {
    status_msg "Configuring environment"
    
    # Create data directory structure
    mkdir -p /app/rootfs/data
    
    # Set default arguments if not provided
    if [ -z "$ARGS" ]; then
        ARGS="-H 0.0.0.0"
    fi
    
    # If login credentials provided but not in arguments
    if [ -n "$USERNAME" ] && [ -n "$PASSWORD" ] && [[ ! "$ARGS" =~ "-L" ]]; then
        ARGS="$ARGS -L $USERNAME:$PASSWORD"
    fi
    
    # Add ports to arguments if not specified
    [[ ! "$ARGS" =~ "-D" ]] && ARGS="$ARGS -D 10020"
    [[ ! "$ARGS" =~ "-M" ]] && ARGS="$ARGS -M 20020"
    
    # Ensure data directory permissions
    chmod -R 777 /app/rootfs/data
}

# Start wrapper service
start_service() {
    status_msg "Starting wrapper service"
    status_msg "Command: ./wrapper $ARGS"
    
    # Change to wrapper directory and run in foreground
    cd /app/wrapper
    exec ./wrapper $ARGS
}

# Main execution flow
main() {
    # Check if running as root
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "Script must be run as root"
    fi

    install_dependencies
    setup_wrapper
    configure_environment
    start_service
}

# Handle environment variables
export USERNAME=${USERNAME:-""}
export PASSWORD=${PASSWORD:-""}
export ARGS=${ARGS:-""}

main
