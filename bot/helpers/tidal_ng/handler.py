import os
import json
import asyncio
import shutil
from config import Config
from ..message import edit_message, send_message
from bot.logger import LOGGER
from ..database.pg_impl import user_set_db, download_history
from bot.helpers.utils import (
    extract_audio_metadata,
    extract_video_metadata,
)
from bot.helpers.uploader import track_upload, album_upload, playlist_upload, music_video_upload
import re

# Define the path to the tidal-dl-ng CLI script
TIDAL_DL_NG_CLI_PATH = "/usr/src/app/tidal-dl-ng/tidal_dl_ng/cli.py"
# Define the path to the settings.json for the CLI tool
TIDAL_DL_NG_SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"

async def log_stderr(stream, bot_msg, user):
    """
    Reads stderr from the subprocess and logs it.
    """
    while True:
        line = await stream.readline()
        if not line:
            break
        output = line.decode('utf-8').strip()
        LOGGER.info(f"[TidalDL-NG-STDERR] {output}")

def get_content_id_from_url(url: str) -> str:
    """Extracts the content ID from a Tidal URL."""
    match = re.search(r'/(track|album|playlist|video)/(\d+)', url)
    return match.group(2) if match else "unknown"

async def start_tidal_ng(link: str, user: dict, options: dict = None):
    """
    Handles downloads using the tidal-dl-ng CLI tool, and then uploads the result.
    """
    bot_msg = user.get('bot_msg')
    original_settings = None
    final_download_path = None
    is_temp_path = False

    try:
        # --- One-time setup & Initial Read ---
        if not os.path.exists(TIDAL_DL_NG_SETTINGS_PATH):
            LOGGER.info("Tidal NG settings file not found. Running one-time setup...")
            await edit_message(bot_msg, "Tidal NG not yet configured. Performing one-time setup...")
            setup_cmd = ["python", TIDAL_DL_NG_CLI_PATH, "cfg"]
            process = await asyncio.create_subprocess_exec(*setup_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Tidal NG one-time setup failed.")
            LOGGER.info("Tidal NG one-time setup successful.")
            await asyncio.sleep(1)

        with open(TIDAL_DL_NG_SETTINGS_PATH, 'r') as f:
            original_settings = json.load(f)

        # --- Execute Download ---
        await edit_message(bot_msg, "🚀 Starting Tidal NG download...")
        cmd = ["python", TIDAL_DL_NG_CLI_PATH, "dl", link, "--output-json"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Log stderr in real-time, capture stdout for JSON parsing
        stderr_task = asyncio.create_task(log_stderr(process.stderr, bot_msg, user))
        stdout, _ = await process.communicate()
        await stderr_task

        if process.returncode != 0:
            raise Exception("Tidal-NG download process failed. Check logs for details.")

        # --- Process and Upload ---
        await edit_message(bot_msg, "📥 Download complete. Processing files...")

        try:
            output_json = json.loads(stdout)
        except json.JSONDecodeError:
            raise Exception("Failed to parse JSON output from tidal-dl-ng. No file paths found.")

        # The output can be a dict (track/video) or a list of dicts (album/playlist)
        if isinstance(output_json, dict):
            items_data = [output_json]
        elif isinstance(output_json, list):
            items_data = output_json
        else:
            raise Exception(f"Unexpected JSON output format: {type(output_json)}")

        if not items_data:
            raise Exception("No files were downloaded (JSON output was empty).")

        downloaded_items = []
        paths_to_clean = set()

        for item_data in items_data:
            file_path = item_data.get('path')
            if not file_path or not os.path.exists(file_path):
                LOGGER.error(f"File path not found in JSON or does not exist: {file_path}")
                continue

            try:
                if file_path.lower().endswith(('.mp4', '.m4v')):
                    metadata = await extract_video_metadata(file_path)
                else:
                    metadata = await extract_audio_metadata(file_path)

                metadata['filepath'] = file_path
                metadata['provider'] = 'Tidal NG'
                downloaded_items.append(metadata)

                # Add the parent directory to the cleanup set
                paths_to_clean.add(os.path.dirname(file_path))

            except Exception as e:
                LOGGER.error(f"Metadata extraction failed for {file_path}: {str(e)}")

        if not downloaded_items:
            raise Exception("Metadata extraction failed for all downloaded files.")

        # Determine content type
        content_type = "track"
        if len(downloaded_items) > 1:
            # Check if all items belong to the same album
            album_titles = {item.get('album') for item in downloaded_items if item.get('album')}
            if len(album_titles) == 1:
                content_type = "album"
            else:
                content_type = "playlist"
        elif downloaded_items[0]['filepath'].lower().endswith(('.mp4', '.m4v')):
            content_type = "video"

        # For albums/playlists, we need a common folder path for the uploader
        # We can use the parent of the first file's parent dir, assuming a structure like .../Artist/Album/track.flac
        common_folder_path = os.path.dirname(os.path.dirname(downloaded_items[0]['filepath'])) if len(paths_to_clean) > 1 else list(paths_to_clean)[0]

        upload_meta = {
            'success': True, 'type': content_type, 'items': downloaded_items,
            'folderpath': common_folder_path, 'provider': 'Tidal NG',
            'title': downloaded_items[0].get('album') if content_type == 'album' else downloaded_items[0].get('title'),
            'artist': downloaded_items[0].get('artist'), 'poster_msg': bot_msg
        }

        # Record in history
        user_id = user.get('user_id')
        content_id = get_content_id_from_url(link)
        # We can't get quality from settings anymore, so let's just put N/A
        download_history.record_download(
            user_id=user_id, provider='Tidal NG', content_type=content_type,
            content_id=content_id, title=upload_meta['title'],
            artist=upload_meta['artist'], quality='N/A'
        )

        # Call the appropriate uploader
        if content_type == 'track':
            await track_upload(downloaded_items[0], user)
        elif content_type == 'video':
            await music_video_upload(downloaded_items[0], user)
        elif content_type == 'album':
            await album_upload(upload_meta, user)
        elif content_type == 'playlist':
            await playlist_upload(upload_meta, user)

        # Cleanup: The uploader functions might delete the folder already.
        # This is a fallback to clean any parent directories left behind.
        # We iterate over a copy as the uploader might modify the underlying folders.
        for path in list(paths_to_clean):
            # The uploader for album/playlist should have already deleted this.
            # This is mainly for single tracks/videos or if the uploader fails.
            if os.path.exists(path):
                LOGGER.info(f"Tidal NG: Cleaning up downloaded content directory: {path}")
                shutil.rmtree(path, ignore_errors=True)

    except Exception as e:
        LOGGER.error(f"An error occurred in start_tidal_ng: {e}", exc_info=True)
        await edit_message(bot_msg, f"❌ **Fatal Error:** An unexpected error occurred: {e}")

    finally:
        if original_settings:
            try:
                with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
                    json.dump(original_settings, f, indent=4)
                LOGGER.info("Tidal-NG settings.json restored to original state.")
            except Exception as e:
                LOGGER.error(f"Failed to restore Tidal-NG settings.json: {e}")
