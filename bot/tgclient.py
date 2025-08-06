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
        await bot_set.login_qobuz()
        await bot_set.login_deezer()
        await bot_set.login_tidal()
        
        # Initialize Apple Music downloader
        if not os.path.exists(Config.DOWNLOADER_PATH):
            LOGGER.error("Apple Music downloader not found! Running installer...")
            subprocess.run([Config.INSTALLER_PATH], check=True)
        
        LOGGER.info("BOT : Started Successfully with Apple Music support")

    async def stop(self, *args):
        await super().stop()
        for client in bot_set.clients:
            await client.session.close()
        LOGGER.info('BOT : Exited Successfully!')

aio = Bot()
