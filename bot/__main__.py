import os
import sys
import subprocess

# Get the parent directory of the current file (bot directory)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the project root directory (apple-music-bot)
project_root = os.path.dirname(current_dir)

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import Config
from bot.logger import LOGGER
from .tgclient import aio

if __name__ == "__main__":
    # Ensure download directory exists
    if not os.path.isdir(Config.LOCAL_STORAGE):
        os.makedirs(Config.LOCAL_STORAGE)
        LOGGER.info(f"Created download directory: {Config.LOCAL_STORAGE}")
    
    # Ensure Apple Music downloader is installed
    if not os.path.exists(Config.DOWNLOADER_PATH):
        LOGGER.warning("Apple Music downloader not found! Attempting installation...")
        try:
            subprocess.run([Config.INSTALLER_PATH], check=True)
            LOGGER.info("Apple Music downloader installed successfully")
        except Exception as e:
            LOGGER.error(f"Apple Music installer failed: {str(e)}")
    
    # Start the bot
    LOGGER.info("Starting Apple Music Downloader Bot...")
    aio.run()
