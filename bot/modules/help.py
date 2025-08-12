from pyrogram import Client, filters
from pyrogram.types import Message

from bot import CMD
from bot.helpers.message import send_message


HELP_TEXT = (
    "Commands:\n"
    "- /start: Start the bot\n"
    "- /download <url> [--options]: Start a download. Reply to a link or pass it directly.\n"
    "  • The bot replies with a Task ID.\n"
    "  • Use /cancel <task_id> to stop that task.\n"
    "  • Use /cancel_all to stop all your running tasks.\n"
    "- /status: Show status of your ongoing tasks (progress, zipping, uploading, uptime)\n"
    "- /settings: Open settings panel\n"
    "- /help: Show this message\n"
)


@Client.on_message(filters.command(CMD.HELP))
async def help_cmd(c: Client, msg: Message):
    await send_message(msg, HELP_TEXT)