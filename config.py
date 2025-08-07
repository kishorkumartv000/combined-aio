import os
import logging
from os import getenv
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)

# Load .env when no ENV is set
if not os.environ.get("ENV"):
    load_dotenv(".env", override=True)

class Config:
    # Telegram
    TG_BOT_TOKEN          = getenv("TG_BOT_TOKEN")
    APP_ID                = int(getenv("APP_ID", "0"))
    API_HASH              = getenv("API_HASH")
    BOT_USERNAME          = getenv("BOT_USERNAME")
    ADMINS                = set(int(x) for x in getenv("ADMINS", "").replace(",", " ").split() if x)

    # Database
    DATABASE_URL          = getenv("DATABASE_URL")

    # Storage and Paths
    UPLOAD_MODE           = getenv("UPLOAD_MODE", "Telegram")
    WORK_DIR              = getenv("WORK_DIR", "./bot/")
    DOWNLOADS_FOLDER      = getenv("DOWNLOADS_FOLDER", "DOWNLOADS")
    LOCAL_STORAGE         = os.path.join(WORK_DIR, DOWNLOADS_FOLDER)
    DOWNLOAD_BASE_DIR     = getenv("DOWNLOAD_BASE_DIR", LOCAL_STORAGE)

    # Naming Formats
    PLAYLIST_NAME_FORMAT  = getenv("PLAYLIST_NAME_FORMAT", "{title} - Playlist")
    TRACK_NAME_FORMAT     = getenv("TRACK_NAME_FORMAT", "{title} - {artist}")

    # Rclone / Index
    RCLONE_CONFIG         = getenv("RCLONE_CONFIG")
    RCLONE_DEST           = getenv("RCLONE_DEST")
    INDEX_LINK            = getenv("INDEX_LINK")

    # Qobuz
    QOBUZ_EMAIL           = getenv("QOBUZ_EMAIL")
    QOBUZ_PASSWORD        = getenv("QOBUZ_PASSWORD")
    QOBUZ_USER            = int(getenv("QOBUZ_USER", "0"))
    QOBUZ_TOKEN           = getenv("QOBUZ_TOKEN")
    QOBUZ_QUALITY         = int(getenv("QOBUZ_QUALITY", "0"))

    # Deezer
    DEEZER_EMAIL          = getenv("DEEZER_EMAIL")
    DEEZER_PASSWORD       = getenv("DEEZER_PASSWORD")
    DEEZER_BF_SECRET      = getenv("DEEZER_BF_SECRET")
    DEEZER_ARL            = getenv("DEEZER_ARL")

    # Tidal
    ENABLE_TIDAL          = getenv("ENABLE_TIDAL", "False")
    TIDAL_MOBILE          = getenv("TIDAL_MOBILE", "False")
    TIDAL_MOBILE_TOKEN    = getenv("TIDAL_MOBILE_TOKEN")
    TIDAL_ATMOS_MOBILE_TOKEN = getenv("TIDAL_ATMOS_MOBILE_TOKEN")
    TIDAL_TV_TOKEN        = getenv("TIDAL_TV_TOKEN")
    TIDAL_TV_SECRET       = getenv("TIDAL_TV_SECRET")
    TIDAL_CONVERT_M4A     = getenv("TIDAL_CONVERT_M4A", "False")
    TIDAL_REFRESH_TOKEN   = getenv("TIDAL_REFRESH_TOKEN")
    TIDAL_COUNTRY_CODE    = getenv("TIDAL_COUNTRY_CODE", "US")
    TIDAL_QUALITY         = getenv("TIDAL_QUALITY")
    TIDAL_SPATIAL         = getenv("TIDAL_SPATIAL")

    # Concurrency
    MAX_WORKERS           = int(getenv("MAX_WORKERS", "5"))

    # Apple Music
    DOWNLOADER_PATH       = getenv("DOWNLOADER_PATH", "/usr/src/app/downloader/am_downloader.sh")
    INSTALLER_PATH        = getenv("INSTALLER_PATH", "/usr/src/app/downloader/install_am_downloader.sh")
    APPLE_DEFAULT_FORMAT  = getenv("APPLE_DEFAULT_FORMAT", "alac")
    APPLE_ALAC_QUALITY    = int(getenv("APPLE_ALAC_QUALITY", "192000"))
    APPLE_ATMOS_QUALITY   = int(getenv("APPLE_ATMOS_QUALITY", "2768"))

    # Optional Bot Settings (via /settings)
    BOT_PUBLIC            = getenv("BOT_PUBLIC", "False")
    ANTI_SPAM             = getenv("ANTI_SPAM", "OFF")
    ART_POSTER            = getenv("ART_POSTER", "False")
    PLAYLIST_SORT         = getenv("PLAYLIST_SORT", "False")
    ARTIST_BATCH_UPLOAD   = getenv("ARTIST_BATCH_UPLOAD", "False")
    PLAYLIST_CONCURRENT   = getenv("PLAYLIST_CONCURRENT", "False")
    PLAYLIST_LINK_DISABLE = getenv("PLAYLIST_LINK_DISABLE", "False")
    ALBUM_ZIP             = getenv("ALBUM_ZIP", "False")
    PLAYLIST_ZIP          = getenv("PLAYLIST_ZIP", "False")
    ARTIST_ZIP            = getenv("ARTIST_ZIP", "False")
    RCLONE_LINK_OPTIONS   = getenv("RCLONE_LINK_OPTIONS", "Index")
