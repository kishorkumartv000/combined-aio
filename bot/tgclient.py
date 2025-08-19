from config import Config
from pyrogram import Client
from .logger import LOGGER
from .settings import bot_set
import subprocess
import os

plugins = dict(
    root="bot/modules"
)

class Bot(Client):
    def __init__(self):
        super().__init__(
            "Apple-Music-Bot",
            api_id=Config.APP_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.TG_BOT_TOKEN,
            plugins=plugins,
            workdir=Config.WORK_DIR,
            workers=Config.MAX_WORKERS
        )

    async def start(self):
        await super().start()

        
        # Initialize Apple Music downloader
        if not os.path.exists(Config.DOWNLOADER_PATH):
            LOGGER.error("Apple Music downloader not found! Running installer...")
            subprocess.run([Config.INSTALLER_PATH], check=True)
        
        # Queue worker: start only if Queue Mode is enabled
        try:
            from .helpers.tasks import task_manager
            from .settings import bot_set
            if getattr(bot_set, 'queue_mode', False):
                await task_manager.start_worker()
        except Exception:
            pass

        LOGGER.info("BOT : Started Successfully with Apple Music support")

    async def stop(self, *args):
        await super().stop()
        for client in bot_set.clients:
            await client.session.close()
        LOGGER.info('BOT : Exited Successfully!')

aio = Bot()
