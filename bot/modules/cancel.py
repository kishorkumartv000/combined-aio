from pyrogram import Client, filters
from pyrogram.types import Message

from bot import CMD
from bot.helpers.tasks import task_manager
from bot.helpers.message import send_message, check_user, fetch_user_details
from bot.settings import bot_set


cancel_cmds = ["cancel"]
if bot_set.bot_username:
	cancel_cmds.append(f"cancel@{bot_set.bot_username}")

@Client.on_message(filters.command(cancel_cmds))
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


cancel_all_cmds = ["cancel_all"]
if bot_set.bot_username:
	cancel_all_cmds.append(f"cancel_all@{bot_set.bot_username}")

@Client.on_message(filters.command(cancel_all_cmds))
async def cancel_all_tasks(c, msg: Message):
	if not await check_user(msg=msg):
		return
	user = await fetch_user_details(msg)
	count = await task_manager.cancel_all(user_id=user['user_id'])
	if count:
		await send_message(msg, f"⏹️ Cancellation requested for {count} task(s)")
	else:
		await send_message(msg, "✅ No running tasks to cancel")


# Queue helpers
queue_list_cmds = ["qqueue", "queue"]
if bot_set.bot_username:
	queue_list_cmds += [f"qqueue@{bot_set.bot_username}", f"queue@{bot_set.bot_username}"]

@Client.on_message(filters.command(queue_list_cmds))
async def list_queue(c, msg: Message):
	if not await check_user(msg=msg):
		return
	from bot.helpers.tasks import task_manager
	items = await task_manager.list_pending(user_id=msg.from_user.id)
	if not items:
		return await send_message(msg, "🕊️ Queue is empty")
	lines = ["📝 Your queue:"]
	for it in items[:15]:
		lines.append(f"{it.get('position')}. {it.get('link')}\n   ID: <code>{it.get('qid')}</code>")
	await send_message(msg, "\n".join(lines))


queue_cancel_cmds = ["qcancel"]
if bot_set.bot_username:
	queue_cancel_cmds.append(f"qcancel@{bot_set.bot_username}")

@Client.on_message(filters.command(queue_cancel_cmds))
async def cancel_queue_item(c, msg: Message):
	if not await check_user(msg=msg):
		return
	parts = msg.text.strip().split()
	if len(parts) < 2:
		return await send_message(msg, "Usage: /qcancel <queue_id>")
	qid = parts[1]
	from bot.helpers.tasks import task_manager
	ok = await task_manager.cancel_pending(qid, user_id=msg.from_user.id)
	if ok:
		await send_message(msg, f"✅ Removed from queue: {qid}")
	else:
		await send_message(msg, f"❌ Queue ID not found: {qid}")