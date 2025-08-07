#!/bin/bash
# Apple Music Downloader - Core Download Functionality with Progress Reporting
set -e

# Explicitly add Go to PATH
export PATH="$PATH:/usr/local/go/bin"

# Display help if no arguments
if [ $# -eq 0 ]; then
    echo "Apple Music Downloader Bot"
    echo "Usage: $0 [OPTIONS] URL"
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
    exit 0
fi

# Change to Go project directory
cd "$HOME/amalac"

# Function to report progress
report_progress() {
    echo "PROGRESS:$1"
}

# Build the download command
cmd=(
    go run main.go
    "$@"
)

# Execute download with progress reporting
echo "Starting Apple Music download..."
report_progress "10"

# Run the command and capture output
"${cmd[@]}" | while IFS= read -r line; do
    # Check for specific progress indicators in the output
    if [[ $line == *"Downloading track"* ]]; then
        report_progress "30"
    elif [[ $line == *"Download complete"* ]]; then
        report_progress "70"
    elif [[ $line == *"Applying metadata"* ]]; then
        report_progress "90"
    fi
    echo "$line"
done

# Final progress
report_progress "100"

# Output success message
echo "Download completed successfully!"
