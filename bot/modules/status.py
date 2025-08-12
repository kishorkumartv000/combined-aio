from pyrogram import Client, filters
from pyrogram.types import Message

from bot import CMD
from bot.helpers.message import send_message
from bot.helpers.tasks import task_manager


@Client.on_message(filters.command(CMD.STATUS))
async def status_cmd(c: Client, msg: Message):
    # Determine user id and list their tasks
    user_id = msg.from_user.id if msg.from_user else None
    tasks = await task_manager.list(user_id=user_id)
    if not tasks:
        return await send_message(msg, "✅ No running tasks.")

    responses = []
    for tid, state in tasks.items():
        # Prefer rendering via attached progress reporter if available
        try:
            if getattr(state, "progress", None):
                progress_text = state.progress._render()
            else:
                progress_text = f"🆔 {tid} • {state.label} • {state.status}"
        except Exception:
            progress_text = f"🆔 {tid} • {state.label} • {state.status}"
        responses.append(progress_text)

    text = "\n\n".join(responses)
    await send_message(msg, text)