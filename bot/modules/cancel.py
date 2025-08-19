
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