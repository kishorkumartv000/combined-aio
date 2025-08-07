import os
import logging
from os import getenv
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)

if not os.environ.get("ENV"):
    load_dotenv('.env', override=True)

class Config:
    # Telegram Configuration
    TG_BOT_TOKEN = getenv("TG_BOT_TOKEN")
    APP_ID = int(getenv("APP_ID"))
    API_HASH = getenv("API_HASH")
    DATABASE_URL = getenv("DATABASE_URL")
    BOT_USERNAME = getenv("BOT_USERNAME")
    ADMINS = set(int(x) for x in getenv("ADMINS").split()) if getenv("ADMINS") else set()

    # Working Directory
    UPLOAD_MODE = getenv("UPLOAD_MODE", "Telegram")  # Default to Telegram
    WORK_DIR = getenv("WORK_DIR", "./bot/")
    DOWNLOADS_FOLDER = getenv("DOWNLOADS_FOLDER", "DOWNLOADS")
    LOCAL_STORAGE = getenv("LOCAL_STORAGE", WORK_DIR + DOWNLOADS_FOLDER)
    
    # Add this new configuration for download base directory
    DOWNLOAD_BASE_DIR = getenv("DOWNLOAD_BASE_DIR", LOCAL_STORAGE)

    # File/Folder Naming
    PLAYLIST_NAME_FORMAT = getenv("PLAYLIST_NAME_FORMAT", "{title} - Playlist")
    TRACK_NAME_FORMAT = getenv("TRACK_NAME_FORMAT", "{title} - {artist}")

    # Rclone/Index Configuration
    RCLONE_CONFIG = getenv("RCLONE_CONFIG")
    RCLONE_DEST = getenv("RCLONE_DEST")
    INDEX_LINK = getenv('INDEX_LINK')

    # Qobuz Configuration
    QOBUZ_EMAIL = getenv("QOBUZ_EMAIL")
    QOBUZ_PASSWORD = getenv("QOBUZ_PASSWORD")
    QOBUZ_USER = getenv("QOBUZ_USER")
    QOBUZ_TOKEN = getenv("QOBUZ_TOKEN")

    # Deezer Configuration
    DEEZER_EMAIL = getenv("DEEZER_EMAIL")
    DEEZER_PASSWORD = getenv("DEEZER_PASSWORD")
    DEEZER_BF_SECRET = getenv("DEEZER_BF_SECRET")
    DEEZER_ARL = getenv("DEEZER_ARL")

    # Tidal configuration
    ENABLE_TIDAL = getenv("ENABLE_TIDAL")
    TIDAL_MOBILE = getenv("TIDAL_MOBILE")
    TIDAL_MOBILE_TOKEN = getenv("TIDAL_MOBILE_TOKEN")
    TIDAL_ATMOS_MOBILE_TOKEN = getenv("TIDAL_ATMOS_MOBILE_TOKEN")
    TIDAL_TV_TOKEN = getenv("TIDAL_TV_TOKEN")
    TIDAL_TV_SECRET = getenv("TIDAL_TV_SECRET")
    TIDAL_CONVERT_M4A = getenv("TIDAL_CONVERT_M4A", False)
    TIDAL_REFRESH_TOKEN = getenv("TIDAL_REFRESH_TOKEN")
    TIDAL_COUNTRY_CODE = getenv("TIDAL_COUNTRY_CODE")

    # Concurrent Workers
    MAX_WORKERS = int(getenv("MAX_WORKERS", 5))

    # Apple Music Configuration
    DOWNLOADER_PATH = getenv("DOWNLOADER_PATH", "./downloader/am_downloader.sh")
    INSTALLER_PATH = getenv("INSTALLER_PATH", "./downloader/install_am_downloader.sh")
    APPLE_DEFAULT_FORMAT = getenv("APPLE_DEFAULT_FORMAT", "alac")
    APPLE_ALAC_QUALITY = getenv("APPLE_ALAC_QUALITY", "192000")
    APPLE_ATMOS_QUALITY = getenv("APPLE_ATMOS_QUALITY", "2768")
