import os
import logging
from bot import Config
from bot.logger import LOGGER
from .tgclient import aio

if __name__ == "__main__":
    # Ensure download directory exists
    if not os.path.isdir(Config.DOWNLOAD_BASE_DIR):
        os.makedirs(Config.DOWNLOAD_BASE_DIR)
        LOGGER.info(f"Created download directory: {Config.DOWNLOAD_BASE_DIR}")
    
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
