from pyrogram import Client, filters
from pyrogram.types import Message

from bot import CMD
from bot.helpers.tasks import task_manager
from bot.helpers.message import send_message, check_user, fetch_user_details
from bot.settings import bot_set


@Client.on_message(filters.command(["cancel", f"cancel@{bot_set.bot_username}"]))
async def cancel_task(c, msg: Message):
    if not await check_user(msg=msg):
        return
    parts = msg.text.strip().split()
    if len(parts) < 2:
        return await send_message(msg, "Usage: /cancel <task_id>")
    task_id = parts[1]
    ok = await task_manager.cancel(task_id)
    if ok:
        await send_message(msg, f"⏹️ Cancellation requested for ID: {task_id}")
    else:
        await send_message(msg, f"❓ Task ID not found: {task_id}")


@Client.on_message(filters.command(["cancel_all", f"cancel_all@{bot_set.bot_username}"]))
async def cancel_all_tasks(c, msg: Message):
    if not await check_user(msg=msg):
        return
    user = await fetch_user_details(msg)
    count = await task_manager.cancel_all(user_id=user['user_id'])
    if count:
        await send_message(msg, f"⏹️ Cancellation requested for {count} task(s)")
    else:
        await send_message(msg, "✅ No running tasks to cancel")