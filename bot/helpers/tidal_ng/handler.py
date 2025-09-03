import os
import json
import asyncio
import shutil
from config import Config
from ..message import edit_message, send_message
from bot.logger import LOGGER

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

        # Avoid flooding Telegram with messages. Only update if the line is not empty.
        if output:
            try:
                # We can make this more sophisticated later by buffering lines
                # or only updating every few seconds. For now, this is fine.
                await edit_message(bot_msg, f"```\n{output}\n```")
            except Exception:
                # Ignore errors from trying to edit the message too often
                pass

async def start_tidal_ng(link: str, user: dict):
    """
    Handles downloads using the tidal-dl-ng CLI tool.

    This function prepares the environment for the CLI tool by:
    1. Determining the correct download path.
    2. Modifying the tool's settings.json to use this path.
    3. Executing the CLI tool as a subprocess.
    4. Providing real-time progress feedback to the user.
    5. Restoring the original settings.json afterwards.
    """
    bot_msg = user.get('bot_msg')

    # 1. Determine the download path
    if Config.TIDAL_NG_DOWNLOAD_PATH:
        download_path = Config.TIDAL_NG_DOWNLOAD_PATH
    else:
        # Use a unique directory for each task within the user's download folder
        download_path = os.path.join(Config.DOWNLOAD_BASE_DIR, str(user.get('user_id')), user.get('task_id'))

    os.makedirs(download_path, exist_ok=True)
    LOGGER.info(f"Tidal-NG download path set to: {download_path}")

    # 2. Modify settings.json
    original_settings = None
    try:
        # Check if the settings file exists
        if not os.path.exists(TIDAL_DL_NG_SETTINGS_PATH):
            error_msg = "Tidal DL NG settings file not found. Please ensure the tool is installed correctly."
            LOGGER.error(error_msg)
            await edit_message(bot_msg, f"❌ **Error:** {error_msg}")
            return

        # Read the original settings
        with open(TIDAL_DL_NG_SETTINGS_PATH, 'r') as f:
            original_settings = json.load(f)

        # Create a copy and update the download path
        new_settings = original_settings.copy()
        new_settings['download_base_path'] = download_path

        # Write the modified settings
        with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
            json.dump(new_settings, f, indent=4)

        # 3. Execute the download
        await edit_message(bot_msg, "🚀 Starting Tidal NG download...")

        cmd = ["python", TIDAL_DL_NG_CLI_PATH, "dl", link]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Concurrently log stdout and stderr
        await asyncio.gather(
            log_progress(process.stdout, bot_msg, user),
            log_progress(process.stderr, bot_msg, user)
        )

        # Wait for the process to complete
        await process.wait()

        if process.returncode == 0:
            LOGGER.info("Tidal-NG download process completed successfully.")
            await edit_message(bot_msg, "✅ Tidal NG download complete. Preparing upload...")
            # The calling function will handle the upload of files from `download_path`
            user['download_path'] = download_path
        else:
            LOGGER.error(f"Tidal-NG download process failed with return code {process.returncode}.")
            await edit_message(bot_msg, f"❌ **Error:** Tidal NG download failed. Check logs for details.")
            # Clean up the failed download directory
            shutil.rmtree(download_path, ignore_errors=True)

    except Exception as e:
        LOGGER.error(f"An error occurred in start_tidal_ng: {e}", exc_info=True)
        await edit_message(bot_msg, f"❌ **Fatal Error:** An unexpected error occurred: {e}")
        if os.path.exists(download_path):
            shutil.rmtree(download_path, ignore_errors=True)

    finally:
        # 4. Restore original settings.json
        if original_settings:
            try:
                with open(TIDAL_DL_NG_SETTINGS_PATH, 'w') as f:
                    json.dump(original_settings, f, indent=4)
                LOGGER.info("Tidal-NG settings.json restored to original state.")
            except Exception as e:
                LOGGER.error(f"Failed to restore Tidal-NG settings.json: {e}")
