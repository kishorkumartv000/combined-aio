import os
import json
import asyncio
import shutil
from config import Config
from ..message import edit_message, send_message
from bot.logger import LOGGER
from ..database.pg_impl import user_set_db

# Define the path to the tidal-dl-ng CLI script
TIDAL_DL_NG_CLI_PATH = "/usr/src/app/tidal-dl-ng/tidal_dl_ng/cli.py"
# Define the path to the settings.json for the CLI tool
TIDAL_DL_NG_SETTINGS_PATH = "/root/.config/tidal_dl_ng/settings.json"

async def log_progress(stream, bot_msg, user):
    """
    Reads a stream (stdout/stderr) from the subprocess and updates the Telegram message.
    """
    while True:
        line = await stream.readline()
        if not line:
            break

        output = line.decode('utf-8').strip()
        LOGGER.info(f"[TidalDL-NG] {output}")

        if output:
            try:
                await edit_message(bot_msg, f"```\n{output}\n```")
            except Exception:
                pass

async def start_tidal_ng(link: str, user: dict):
    """
    Handles downloads using the tidal-dl-ng CLI tool.

    This function prepares the environment for the CLI tool by:
    1. Checking for and performing a one-time setup if needed.
    2. Determining the correct download path.
    3. Modifying the tool's settings.json with user preferences.
    4. Executing the CLI tool as a subprocess.
    5. Providing real-time progress feedback.
    6. Restoring the original settings.json afterwards.
    """
    bot_msg = user.get('bot_msg')

    # 1. Determine the download path
    if Config.TIDAL_NG_DOWNLOAD_PATH:
        download_path = Config.TIDAL_NG_DOWNLOAD_PATH
    else:
        download_path = os.path.join(Config.DOWNLOAD_BASE_DIR, str(user.get('user_id')), user.get('task_id'))

    os.makedirs(download_path, exist_ok=True)
    LOGGER.info(f"Tidal-NG download path set to: {download_path}")

    original_settings = None
    try:
        # One-time setup: Check if settings.json exists. If not, create it.
        if not os.path.exists(TIDAL_DL_NG_SETTINGS_PATH):
            LOGGER.info(f"Tidal NG settings file not found. Running one-time setup...")
            await edit_message(bot_msg, "Tidal NG not yet configured. Performing one-time setup...")

            setup_cmd = ["python", TIDAL_DL_NG_CLI_PATH, "cfg"]
            process = await asyncio.create_subprocess_exec(
                *setup_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode != 0:
                raise Exception("Tidal NG one-time setup failed.")

            LOGGER.info("Tidal NG one-time setup successful.")
            await asyncio.sleep(1)

        # Read the original settings
        with open(TIDAL_DL_NG_SETTINGS_PATH, 'r') as f:
            original_settings = json.load(f)

        # Create a copy and update the settings
        new_settings = original_settings.copy()
        new_settings['download_base_path'] = download_path

        def apply_user_setting(settings_dict, user_id, db_key, json_key, is_bool=False, is_int=False):
            value_str = user_set_db.get_user_setting(user_id, db_key)
            if value_str is not None:
                value = value_str
                if is_bool:
                    value = value_str == 'True'
                elif is_int:
                    try:
                        value = int(value_str)
                    except ValueError:
                        return
                settings_dict[json_key] = value
                LOGGER.info(f"Applying user setting for {user_id}: {json_key} = {value}")

        user_id = user.get('user_id')
        if user_id:
            apply_user_setting(new_settings, user_id, 'tidal_ng_quality', 'quality_audio')
            apply_user_setting(new_settings, user_id, 'tidal_ng_lyrics', 'lyrics_embed', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_replay_gain', 'metadata_replay_gain', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_lyrics_file', 'lyrics_file', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_playlist_create', 'playlist_create', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_cover_dim', 'metadata_cover_dimension', is_int=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_quality', 'quality_video')
            apply_user_setting(new_settings, user_id, 'tidal_ng_symlink', 'symlink_to_track', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_convert', 'video_convert_mp4', is_bool=True)
            apply_user_setting(new_settings, user_id, 'tidal_ng_video_download', 'video_download', is_bool=True)

        with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
            json.dump(new_settings, f, indent=4)

        await edit_message(bot_msg, "🚀 Starting Tidal NG download...")

        cmd = ["python", TIDAL_DL_NG_CLI_PATH, "dl", link]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.gather(
            log_progress(process.stdout, bot_msg, user),
            log_progress(process.stderr, bot_msg, user)
        )

        await process.wait()

        if process.returncode == 0:
            LOGGER.info("Tidal-NG download process completed successfully.")
            await edit_message(bot_msg, "✅ Tidal NG download complete. Preparing upload...")
            user['download_path'] = download_path
        else:
            raise Exception("Tidal-NG download process failed.")

    except Exception as e:
        LOGGER.error(f"An error occurred in start_tidal_ng: {e}", exc_info=True)
        await edit_message(bot_msg, f"❌ **Fatal Error:** An unexpected error occurred: {e}")
        if os.path.exists(download_path):
            shutil.rmtree(download_path, ignore_errors=True)

    finally:
        if original_settings:
            try:
                with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
                    json.dump(original_settings, f, indent=4)
                LOGGER.info("Tidal-NG settings.json restored to original state.")
            except Exception as e:
                LOGGER.error(f"Failed to restore Tidal-NG settings.json: {e}")
