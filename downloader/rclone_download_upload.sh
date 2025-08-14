#!/bin/bash
# Apple Music Downloader with Cloud Copy
set -e

# Explicitly add Go to PATH
export PATH="$PATH:/usr/local/go/bin"

# Load configuration
CONFIG_FILE="$HOME/amalac/rcloner_downloader.conf"
[ ! -f "$CONFIG_FILE" ] && { echo "Configuration missing! Run installer first."; exit 1; }
source "$CONFIG_FILE"

# Use custom rclone config if specified
RCLONE_CMD="rclone"
[ -n "$RCLONE_CONFIG_PATH" ] && RCLONE_CMD="rclone --config $RCLONE_CONFIG_PATH"

# Display help if no arguments
if [ $# -eq 0 ]; then
    echo "Apple Music Downloader with Cloud Copy"
    echo "Usage: $0 [OPTIONS] URL1 [URL2 ...]"
    echo ""
    echo "Download Options:"
    echo "  --aac                    Enable AAC download mode"
    echo "  --aac-type TYPE          AAC type: aac, aac-binaural, aac-downmix (default: aac-lc)"
    echo "  --alac-max QUALITY       Max ALAC quality (default: 192000)"
    echo "  --all-album              Download all artist albums"
    echo "  --atmos                  Enable Atmos download mode"
    echo "  --atmos-max QUALITY      Max Atmos quality (default: 2768)"
    echo "  --debug                  Enable debug mode"
    echo "  --mv-audio-type TYPE     MV audio type: atmos, ac3, aac (default: atmos)"
    echo "  --mv-max QUALITY         Max MV quality (default: 2160)"
    echo "  --select                 Enable selective download"
    echo "  --song                   Enable single song download mode"
    echo ""
    echo "Cloud Options:"
    echo "  ACTIVE_REMOTES: ${ACTIVE_REMOTES[@]}"
    echo "  CLOUD_BASE_PATH: $CLOUD_BASE_PATH"
    echo "  DELETE_AFTER_SYNC: $DELETE_AFTER_SYNC"
    echo ""
    echo "Example:"
    echo "  $0 --atmos --alac-max 256000 --all-album \"https://music.apple.com/...\""
    exit 0
fi

# Get available remotes
AVAILABLE_REMOTES=$($RCLONE_CMD listremotes | cut -d: -f1)

# Handle remote selection
select_remotes() {
    # Check if ACTIVE_REMOTES is set and valid
    if [ ${#ACTIVE_REMOTES[@]} -gt 0 ]; then
        for remote in "${ACTIVE_REMOTES[@]}"; do
            if ! echo "$AVAILABLE_REMOTES" | grep -q "^$remote$"; then
                echo "ERROR: Remote '$remote' not found!"
                echo "Available remotes: $AVAILABLE_REMOTES"
                exit 1
            fi
        done
        REMOTES=("${ACTIVE_REMOTES[@]}")
        return
    fi
    
    # Fallback to first available remote
    FIRST_REMOTE=$(echo "$AVAILABLE_REMOTES" | head -n1)
    if [ -n "$FIRST_REMOTE" ]; then
        echo "Using first available remote: $FIRST_REMOTE"
        REMOTES=("$FIRST_REMOTE")
        return
    fi
    
    echo "ERROR: No rclone remotes configured!"
    echo "1. Run 'rclone config' to create a remote"
    echo "2. Or set ACTIVE_REMOTES in $CONFIG_FILE"
    exit 1
}

# Copy function (simple recursive copy)
copy_to_cloud() {
    local status=0
    
    for remote in "${REMOTES[@]}"; do
        echo "Copying to $remote..."
        
        # Copy entire music directory
        $RCLONE_CMD copy "$MUSIC_BASE_DIR" "$remote:$CLOUD_BASE_PATH" \
            --create-empty-src-dirs \
            --progress \
            --transfers $SYNC_CONCURRENCY \
            --log-file "$LOG_FILE" || status=1
    done
    
    [ $status -ne 0 ] && { echo "ERROR: Copy failed! Check $LOG_FILE"; exit 1; }
    echo "Cloud copy completed successfully!"
    
    # Cleanup if enabled
    if [ "$DELETE_AFTER_SYNC" = true ]; then
        echo "Cleaning local files..."
        rm -rf "${ALAC_DIR:?}/"*
        rm -rf "${ATMOS_DIR:?}/"*
    fi
}

# Download function with option handling
download_content() {
    echo "Starting download with options: $@"
    cd "$HOME/amalac"
    
    # Build the command with all arguments
    go run main.go "$@"
    
    echo "Download completed!"
}

# Main process
echo "=== Starting Apple Music Download ==="
select_remotes
download_content "$@"
copy_to_cloud

echo "=== Operation Complete ==="
echo "Downloaded and copied content"
echo "Cloud location: $CLOUD_BASE_PATH"
echo "Log file: $LOG_FILE"
