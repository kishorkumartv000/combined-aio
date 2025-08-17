from bot import CMD
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

import bot.helpers.translations as lang
import asyncio

from ..settings import bot_set
from ..helpers.buttons.settings import *
from ..helpers.database.pg_impl import set_db
from ..helpers.message import send_message, edit_message, check_user, fetch_user_details
from ..helpers.state import conversation_state



@Client.on_message(filters.command(CMD.SETTINGS))
async def settings(c, message):
    if await check_user(message.from_user.id, restricted=True):
        user = await fetch_user_details(message)
        await send_message(user, lang.s.INIT_SETTINGS_PANEL, markup=main_menu())


@Client.on_callback_query(filters.regex(pattern=r"^corePanel"))
async def core_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        await edit_message(
            cb.message,
            lang.s.CORE_PANEL,
            core_buttons()
        )


# New: Rclone settings panel
@Client.on_callback_query(filters.regex(pattern=r"^rclonePanel"))
async def rclone_panel_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        await edit_message(
            cb.message,
            "Rclone Settings",
            rclone_buttons()
        )

# Simple in-memory flag to accept next document as rclone.conf
_import_waiting = set()

@Client.on_callback_query(filters.regex(pattern=r"^rcloneImport"))
async def rclone_import_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        _import_waiting.add(cb.from_user.id)
        await edit_message(cb.message, "Please send your rclone.conf as a document now.")

@Client.on_message(filters.document)
async def handle_rclone_conf_upload(client, message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        if user_id not in _import_waiting:
            return
        if not message.document:
            return
        # Only accept a file named rclone.conf or any .conf
        filename = (message.document.file_name or '').lower()
        if 'rclone' not in filename and not filename.endswith('.conf'):
            return
        # Download to a temp path and move to ./rclone.conf
        temp_path = await client.download_media(message, file_name='rclone.conf.tmp')
        import os
        if os.path.exists('rclone.conf'):
            os.remove('rclone.conf')
        os.replace(temp_path, 'rclone.conf')
        _import_waiting.discard(user_id)
        await send_message(message, "✅ rclone.conf imported successfully.")
    except Exception:
        try:
            await send_message(message, "❌ Failed to import rclone.conf.")
        except Exception:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDelete"))
async def rclone_delete_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        import os
        try:
            if os.path.exists('rclone.conf'):
                os.remove('rclone.conf')
            # Refresh panel regardless
            await rclone_panel_cb(client, cb)
        except Exception:
            await edit_message(cb.message, "❌ Failed to delete rclone.conf", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneListRemotes"))
async def rclone_list_remotes_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        import asyncio
        import os
        if not os.path.exists('rclone.conf'):
            return await edit_message(cb.message, "rclone.conf not found.", markup=rclone_buttons())
        # Run rclone listremotes using our config
        try:
            proc = await asyncio.create_subprocess_shell(
                'rclone listremotes --config ./rclone.conf | cat',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                remotes = out.decode().strip() or "(no remotes)"
                await edit_message(cb.message, f"Available remotes:\n<code>{remotes}</code>", markup=rclone_buttons())
            else:
                await edit_message(cb.message, f"Failed to list remotes:\n<code>{err.decode().strip()}</code>", markup=rclone_buttons())
        except Exception as e:
            await edit_message(cb.message, f"Error: {e}", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneSend"))
async def rclone_send_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        import os
        if not os.path.exists('rclone.conf'):
            return await edit_message(cb.message, "rclone.conf not found.", markup=rclone_buttons())
        # Send the file as document
        try:
            await send_message(cb, './rclone.conf', 'doc')
        except Exception:
            await edit_message(cb.message, "❌ Failed to send rclone.conf", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneSelectRemote"))
async def rclone_select_remote_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        import asyncio, os
        if not os.path.exists('rclone.conf'):
            return await edit_message(cb.message, "rclone.conf not found.", markup=rclone_buttons())
        try:
            proc = await asyncio.create_subprocess_shell(
                'rclone listremotes --config ./rclone.conf | cat',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode != 0:
                return await edit_message(cb.message, f"Failed to list remotes:\n<code>{err.decode().strip()}</code>", markup=rclone_buttons())
            remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
            if not remotes:
                return await edit_message(cb.message, "No remotes configured.", markup=rclone_buttons())
            # Build buttons for each remote
            rows = []
            for r in remotes:
                rows.append([InlineKeyboardButton(r, callback_data=f"rcloneApplyRemote|{r}")])
            rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])
            return await edit_message(cb.message, "Select remote:", markup=InlineKeyboardMarkup(rows))
        except Exception as e:
            return await edit_message(cb.message, f"Error: {e}", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneApplyRemote\|"))
async def rclone_apply_remote_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            remote = cb.data.split('|', 1)[1]
            # Preserve current path
            suffix = getattr(bot_set, 'rclone_dest_path', '')
            bot_set.rclone_remote = remote
            if bot_set.rclone_remote:
                bot_set.rclone_dest = f"{bot_set.rclone_remote}:{suffix}" if suffix else f"{bot_set.rclone_remote}:"
            else:
                bot_set.rclone_dest = ''
            set_db.set_variable('RCLONE_REMOTE', bot_set.rclone_remote)
            set_db.set_variable('RCLONE_DEST', bot_set.rclone_dest)
            await rclone_panel_cb(client, cb)
        except Exception:
            await edit_message(cb.message, "❌ Failed to set remote", markup=rclone_buttons())

# Capture destination path via next text message after tapping the button
_dest_path_waiting = set()

@Client.on_callback_query(filters.regex(pattern=r"^rcloneSetDestPath"))
async def rclone_set_dest_path_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        # Offer both methods: type text or browse
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Type path manually", callback_data="rcloneDestPathType")],
            [InlineKeyboardButton("Browse folders", callback_data="rcloneDestPathBrowseStart")],
            [InlineKeyboardButton("🔙 Back", callback_data="rclonePanel")]
        ])
        await edit_message(cb.message, "Choose how to set destination path:", buttons)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathType$"))
async def rclone_dest_path_type_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        _dest_path_waiting.add(cb.from_user.id)
        await edit_message(cb.message, "Send destination path suffix (e.g., AppleMusic or AppleMusic/alac). Empty to use remote root.")

@Client.on_message(filters.text, group=10)
async def handle_dest_path_text(client, message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        if user_id not in _dest_path_waiting:
            return
        raw = (message.text or '').strip()
        text = raw.strip('/')
        # Update bot_set and DB
        bot_set.rclone_dest_path = text
        # Build final
        remote = getattr(bot_set, 'rclone_remote', '')
        if remote:
            final = f"{remote}:{text}" if text else f"{remote}:"
        else:
            final = text
        bot_set.rclone_dest = final
        set_db.set_variable('RCLONE_DEST_PATH', text)
        set_db.set_variable('RCLONE_DEST', final)
        _dest_path_waiting.discard(user_id)
        await send_message(message, f"✅ Destination set to: <code>{final or '(unset)'}</code>")
    except Exception:
        try:
            await send_message(message, "❌ Failed to set destination path.")
        except Exception:
            pass

# --- Browse-based destination path selection ---

def _get_rclone_config_arg() -> str:
    import os
    from config import Config
    try:
        if getattr(Config, "RCLONE_CONFIG", None) and os.path.exists(Config.RCLONE_CONFIG):
            return f'--config "{Config.RCLONE_CONFIG}"'
    except Exception:
        pass
    for p in ("/workspace/rclone.conf", "rclone.conf"):
        try:
            if os.path.exists(p):
                return f'--config "{p}"'
        except Exception:
            continue
    return ""

async def _list_remote_dirs(remote: str, path: str) -> list:
    import asyncio
    remote = (remote or "").rstrip(":")
    norm_path = (path or "").strip("/")
    base = f"{remote}:" if norm_path == "" else f"{remote}:{norm_path}/"
    cfg = _get_rclone_config_arg()
    cmd = f'rclone lsf --dirs-only {cfg} "{base}"'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(err.decode().strip() or 'lsf failed')
    names = []
    for line in out.decode().splitlines():
        name = line.strip().rstrip("/")
        if name:
            names.append(name)
    return names

async def _render_browse(client, cb_or_msg, path: str):
    # Ensure remote exists
    remote = getattr(bot_set, 'rclone_remote', '')
    if not remote:
        return await edit_message(cb_or_msg.message if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg, "Please select a remote first.", rclone_buttons())
    try:
        names = await _list_remote_dirs(remote, path)
    except Exception as e:
        return await edit_message(cb_or_msg.message if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg, f"Failed to list folders: {e}", rclone_buttons())

    # Save current state
    user_id = cb_or_msg.from_user.id if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg.from_user.id
    state = await conversation_state.get(user_id) or {}
    data = state.get('data', {})
    data.update({
        'browse_path': path,
        'browse_entries': names
    })
    await conversation_state.update(user_id, stage='rclone_browse', **data)

    # Build UI with pagination
    PAGE_SIZE = 15
    # Read current page from state
    user_id = cb_or_msg.from_user.id if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg.from_user.id
    st = await conversation_state.get(user_id) or {}
    pg = 0
    try:
        pg = int((st.get('data') or {}).get('browse_page', 0) or 0)
    except Exception:
        pg = 0
    total = len(names)
    max_page = 0 if total == 0 else (total - 1) // PAGE_SIZE
    if pg < 0:
        pg = 0
    if pg > max_page:
        pg = max_page
    start = pg * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []
    for idx in range(start, end):
        name = names[idx]
        rows.append([InlineKeyboardButton(name, callback_data=f"rcloneDestPathCd|{idx}")])

    # Page navigation
    nav = []
    if pg > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"rcloneDestPathPage|{pg-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"rcloneDestPathPage|{pg+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("Select here", callback_data="rcloneDestPathSelectHere")])
    # Up button if not root
    if path:
        rows.append([InlineKeyboardButton("⬆️ Up", callback_data="rcloneDestPathUp")])
    # Always show root shortcut
    rows.append([InlineKeyboardButton("🏠 Root", callback_data="rcloneDestPathRoot")])
    rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])

    title = f"Browsing: /{path}" if path else "Browsing: /"
    await edit_message(cb_or_msg.message if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg, title, InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathBrowseStart$"))
async def rclone_dest_path_browse_start_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        # Initialize browse at root by default
        await _render_browse(client, cb, '')

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathPage\|"))
async def rclone_dest_path_page_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            pg = int(cb.data.split('|', 1)[1])
        except Exception:
            return
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        data['browse_page'] = pg
        await conversation_state.update(cb.from_user.id, stage='rclone_browse', **data)
        await _render_browse(client, cb, data.get('browse_path', ''))

# Update cd/up/root to reset page index
@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathCd\|"))
async def rclone_dest_path_cd_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        entries = data.get('browse_entries') or []
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        if idx < 0 or idx >= len(entries):
            return await _render_browse(client, cb, data.get('browse_path', ''))
        name = entries[idx]
        base = data.get('browse_path', '')
        new_path = f"{base}/{name}" if base else name
        data['browse_page'] = 0
        await conversation_state.update(cb.from_user.id, stage='rclone_browse', **data)
        await _render_browse(client, cb, new_path)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathUp$"))
async def rclone_dest_path_up_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        base = data.get('browse_path', '')
        if not base:
            data['browse_page'] = 0
            await conversation_state.update(cb.from_user.id, stage='rclone_browse', **data)
            return await _render_browse(client, cb, '')
        parts = [p for p in base.split('/') if p]
        new_path = '/'.join(parts[:-1])
        data['browse_page'] = 0
        await conversation_state.update(cb.from_user.id, stage='rclone_browse', **data)
        await _render_browse(client, cb, new_path)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathRoot$"))
async def rclone_dest_path_root_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        data['browse_page'] = 0
        await conversation_state.update(cb.from_user.id, stage='rclone_browse', **data)
        await _render_browse(client, cb, '')

@Client.on_callback_query(filters.regex(pattern=r"^rcloneDestPathSelectHere$"))
async def rclone_dest_path_select_here_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        path = data.get('browse_path', '')
        # Persist
        bot_set.rclone_dest_path = path
        remote = getattr(bot_set, 'rclone_remote', '')
        final = f"{remote}:{path}" if remote else path
        bot_set.rclone_dest = final
        set_db.set_variable('RCLONE_DEST_PATH', path)
        set_db.set_variable('RCLONE_DEST', final)
        await rclone_panel_cb(client, cb)


@Client.on_callback_query(filters.regex(pattern=r"^upload"))
async def upload_mode_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        modes = ['Local', 'Telegram']
        modes_count = 2
        if bot_set.rclone:
            modes.append('RCLONE')
            modes_count+=1

        current = modes.index(bot_set.upload_mode)
        nexti = (current + 1) % modes_count
        bot_set.upload_mode = modes[nexti]
        set_db.set_variable('UPLOAD_MODE', modes[nexti])
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^vidUploadType"))
async def video_upload_type_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            # toggle
            bot_set.video_as_document = not bool(getattr(bot_set, 'video_as_document', False))
            set_db.set_variable('VIDEO_AS_DOCUMENT', bot_set.video_as_document)
        except Exception:
            pass
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^toggleExtractCover$"))
async def toggle_extract_cover_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            bot_set.extract_embedded_cover = not bool(getattr(bot_set, 'extract_embedded_cover', True))
            set_db.set_variable('EXTRACT_EMBEDDED_COVER', bot_set.extract_embedded_cover)
        except Exception:
            pass
        try:
            await core_cb(client, cb)
        except:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^linkOption"))
async def link_option_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        options = ['False', 'Index', 'RCLONE', 'Both']
        current = options.index(bot_set.link_options)
        nexti = (current + 1) % 4
        bot_set.link_options = options[nexti]
        set_db.set_variable('RCLONE_LINK_OPTIONS', options[nexti])
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^albArt"))
async def alb_art_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        art_post = bot_set.art_poster
        art_post = False if art_post else True
        bot_set.art_poster = art_post
        set_db.set_variable('ART_POSTER', art_post)
        try:
            await core_cb(client, cb)
        except:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^playCONC"))
async def playlist_conc_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        play_conc = bot_set.playlist_conc
        play_conc = False if play_conc else True
        bot_set.playlist_conc = play_conc
        set_db.set_variable('PLAYLIST_CONCURRENT', play_conc)
        try:
            await core_cb(client, cb)
        except:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^artBATCH"))
async def artist_conc_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        artist_batch = bot_set.artist_batch
        artist_batch = False if artist_batch else True
        bot_set.artist_batch = artist_batch
        set_db.set_variable('ARTIST_BATCH_UPLOAD', artist_batch)
        try:
            await core_cb(client, cb)
        except:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^sortPlay"))
async def playlist_sort_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        sort = bot_set.playlist_sort
        sort = False if sort else True
        bot_set.playlist_sort = sort
        set_db.set_variable('PLAYLIST_SORT', sort)
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^playZip"))
async def playlist_zip_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        option = bot_set.playlist_zip
        option = False if option else True
        bot_set.playlist_zip = option
        set_db.set_variable('PLAYLIST_ZIP', option)
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^sortLinkPlay"))
async def playlist_disable_zip_link(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        option = bot_set.disable_sort_link
        option = False if option else True
        bot_set.disable_sort_link = option
        set_db.set_variable('PLAYLIST_LINK_DISABLE', option)
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^artZip"))
async def artist_zip_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        option = bot_set.artist_zip
        option = False if option else True
        bot_set.artist_zip = option
        set_db.set_variable('ARTIST_ZIP', option)
        try:
            await core_cb(client, cb)
        except:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^albZip"))
async def album_zip_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        option = bot_set.album_zip
        option = False if option else True
        bot_set.album_zip = option
        set_db.set_variable('ALBUM_ZIP', option)
        try:
            await core_cb(client, cb)
        except:
            pass



#--------------------

# COMMON

#--------------------
@Client.on_callback_query(filters.regex(pattern=r"^main_menu"))
async def main_menu_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            await edit_message(cb.message, lang.s.INIT_SETTINGS_PANEL, markup=main_menu())
        except:
            pass

@Client.on_callback_query(filters.regex(pattern=r"^close"))
async def close_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        try:
            await client.delete_messages(
                chat_id=cb.message.chat.id,
                message_ids=cb.message.id
            )
        except:
            pass

@Client.on_message(filters.command(CMD.BAN))
async def ban(client:Client, msg:Message):
    if await check_user(msg.from_user.id, restricted=True):
        try:
            id = int(msg.text.split(" ", maxsplit=1)[1])
        except:
            await send_message(msg, lang.s.BAN_AUTH_FORMAT)
            return

        user = False if str(id).startswith('-100') else True
        if user:
            if id in bot_set.auth_users:
                bot_set.auth_users.remove(id)
                set_db.set_variable('AUTH_USERS', str(bot_set.auth_users))
            else: await send_message(msg, lang.s.USER_DOEST_EXIST)
        else:
            if id in bot_set.auth_chats:
                bot_set.auth_chats.remove(id)
                set_db.set_variable('AUTH_CHATS', str(bot_set.auth_chats))
            else: await send_message(msg, lang.s.USER_DOEST_EXIST)
        await send_message(msg, lang.s.BAN_ID)
        

@Client.on_message(filters.command(CMD.AUTH))
async def auth(client:Client, msg:Message):
    if await check_user(msg.from_user.id, restricted=True):
        try:
            id = int(msg.text.split(" ", maxsplit=1)[1])
        except:
            await send_message(msg, lang.s.BAN_AUTH_FORMAT)
            return

        user = False if str(id).startswith('-100') else True
        if user:
            if id not in bot_set.auth_users:
                bot_set.auth_users.append(id)
                set_db.set_variable('AUTH_USERS', str(bot_set.auth_users))
            else: await send_message(msg, lang.s.USER_EXIST)
        else:
            if id not in bot_set.auth_chats:
                bot_set.auth_chats.append(id)
                set_db.set_variable('AUTH_CHATS', str(bot_set.auth_chats))
            else: await send_message(msg, lang.s.USER_EXIST)
        await send_message(msg, lang.s.AUTH_ID)


@Client.on_message(filters.command(CMD.LOG))
async def send_log(client:Client, msg:Message):
    if await check_user(msg.from_user.id, restricted=True):
        user = await fetch_user_details(msg)
        await send_message(
            user, 
            './bot/bot_logs.log',
            'doc'
        )

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCloudCopyStart$"))
async def rclone_cloud_copy_start_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        import os
        if not os.path.exists('rclone.conf'):
            return await edit_message(cb.message, "rclone.conf not found.", markup=rclone_buttons())
        # List remotes to start picking source
        try:
            proc = await asyncio.create_subprocess_shell(
                'rclone listremotes --config ./rclone.conf | cat',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode != 0:
                return await edit_message(cb.message, f"Failed to list remotes:\n<code>{err.decode().strip()}</code>", markup=rclone_buttons())
            remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
            if not remotes:
                return await edit_message(cb.message, "No remotes configured.", markup=rclone_buttons())
            from ..helpers.state import conversation_state
            await conversation_state.start(cb.from_user.id, 'rclone_cc_source_remote', {'remotes': remotes, 'src_remote': None, 'src_path': '', 'dst_remote': None, 'dst_path': ''})
            rows = [[InlineKeyboardButton(r, callback_data=f"rcloneCcPickSrcRemote|{idx}")] for idx, r in enumerate(remotes[:25])]
            rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])
            await edit_message(cb.message, "Select SOURCE remote:", InlineKeyboardMarkup(rows))
        except Exception as e:
            await edit_message(cb.message, f"Error: {e}", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcPickSrcRemote\|"))
async def rclone_cc_pick_src_remote(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        remotes = data.get('remotes') or []
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        if idx < 0 or idx >= len(remotes):
            return await rclone_cloud_copy_start_cb(client, cb)
        src_remote = remotes[idx]
        await conversation_state.update(cb.from_user.id, stage='rclone_cc_browse_src', src_remote=src_remote, src_path='')
        await _rclone_cc_render_browse(client, cb, which='src', include_files=True)

async def _rclone_cc_list(remote: str, path: str, include_files: bool):
    import asyncio
    # Directories
    cfg = _get_rclone_config_arg()
    base = f"{remote}:{path.strip('/')}/" if path else f"{remote}:"
    cmd_dirs = f'rclone lsf --dirs-only {cfg} "{base}"'
    proc = await asyncio.create_subprocess_shell(
        cmd_dirs,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out_d, err_d = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(err_d.decode().strip() or 'lsf dirs failed')
    dirs = [line.strip().rstrip('/') for line in out_d.decode().splitlines() if line.strip()]
    files = []
    if include_files:
        cmd_files = f'rclone lsf --files-only {cfg} "{base}"'
        p2 = await asyncio.create_subprocess_shell(
            cmd_files,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out_f, err_f = await p2.communicate()
        if p2.returncode != 0:
            # If file listing fails, keep dirs at least
            files = []
        else:
            files = [line.strip() for line in out_f.decode().splitlines() if line.strip()]
    return dirs, files

async def _rclone_cc_render_browse(client, cb_or_msg, which: str, include_files: bool):
    from ..helpers.state import conversation_state
    state = await conversation_state.get(cb_or_msg.from_user.id) or {}
    data = state.get('data', {})
    base_path = data.get(f'{which}_path', '')
    remote = data.get(f'{which}_remote')
    try:
        dirs, files = await _rclone_cc_list(remote, base_path, include_files)
    except Exception as e:
        return await edit_message(cb_or_msg.message if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg, f"Failed to list: {e}", rclone_buttons())
    # Save entries
    await conversation_state.update(cb_or_msg.from_user.id, **{f'{which}_entries': {'dirs': dirs, 'files': files}})

    # Pagination settings
    PAGE_SIZE = 15
    page_key = f"{which}_page"
    try:
        page = int(data.get(page_key, 0) or 0)
    except Exception:
        page = 0

    # Build combined list with type tagging but keep original indices
    combined = [("dir", name, i) for i, name in enumerate(dirs)]
    if include_files:
        combined += [("file", name, i) for i, name in enumerate(files)]
    total = len(combined)

    # Clamp page
    max_page = 0 if total == 0 else (total - 1) // PAGE_SIZE
    if page < 0:
        page = 0
        await conversation_state.update(cb_or_msg.from_user.id, **{page_key: page})

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []
    for etype, name, idx in combined[start:end]:
        if etype == 'dir':
            rows.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"rcloneCcCd|{which}|{idx}")])
        else:
            rows.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"rcloneCcPickFile|{which}|{idx}")])

    # Page navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"rcloneCcPage|{which}|{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"rcloneCcPage|{which}|{page+1}"))
    if nav:
        rows.append(nav)

    # Actions
    if base_path:
        rows.append([InlineKeyboardButton("⬆️ Up", callback_data=f"rcloneCcUp|{which}")])
    rows.append([InlineKeyboardButton("Select this folder", callback_data=f"rcloneCcSelectFolder|{which}")])
    rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])
    title = f"Browsing {which.upper()} {remote}: /{base_path}" if base_path else f"Browsing {which.upper()} {remote}: /"
    await edit_message(cb_or_msg.message if isinstance(cb_or_msg, CallbackQuery) else cb_or_msg, title, InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcCd\|"))
async def rclone_cc_cd_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        _, which, idx_str = cb.data.split('|', 2)
        idx = int(idx_str) if idx_str.isdigit() else -1
        state = await conversation_state.get(cb.from_user.id) or {}
        entries = (state.get('data', {}).get(f'{which}_entries') or {}).get('dirs') or []
        if idx < 0 or idx >= len(entries):
            return await _rclone_cc_render_browse(client, cb, which=which, include_files=(which=='src'))
        base = state.get('data', {}).get(f'{which}_path', '')
        new_path = f"{base}/{entries[idx]}" if base else entries[idx]
        await conversation_state.update(cb.from_user.id, **{f'{which}_path': new_path, f'{which}_page': 0})
        await _rclone_cc_render_browse(client, cb, which=which, include_files=(which=='src'))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcUp\|"))
async def rclone_cc_up_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        _, which = cb.data.split('|', 1)
        state = await conversation_state.get(cb.from_user.id) or {}
        base = state.get('data', {}).get(f'{which}_path', '')
        parts = [p for p in base.split('/') if p]
        new_path = '/'.join(parts[:-1])
        await conversation_state.update(cb.from_user.id, **{f'{which}_path': new_path, f'{which}_page': 0})
        await _rclone_cc_render_browse(client, cb, which=which, include_files=(which=='src'))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcPickFile\|"))
async def rclone_cc_pick_file_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        _, which, idx_str = cb.data.split('|', 2)
        if which != 'src':
            return
        idx = int(idx_str) if idx_str.isdigit() else -1
        state = await conversation_state.get(cb.from_user.id) or {}
        files = (state.get('data', {}).get('src_entries') or {}).get('files') or []
        if idx < 0 or idx >= len(files):
            return await _rclone_cc_render_browse(client, cb, which='src', include_files=True)
        base = state.get('data', {}).get('src_path', '')
        # Select exact file under base
        selected = f"{base}/{files[idx]}" if base else files[idx]
        await conversation_state.update(cb.from_user.id, src_file=selected)
        # Move on to destination selection
        await _rclone_cc_pick_destination_remote(client, cb)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcSelectFolder\|"))
async def rclone_cc_select_folder_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        _, which = cb.data.split('|', 1)
        state = await conversation_state.get(cb.from_user.id) or {}
        base = state.get('data', {}).get(f'{which}_path', '')
        if which == 'src':
            await conversation_state.update(cb.from_user.id, src_file=None, src_page=0)
            # Proceed to destination remote select
            await _rclone_cc_pick_destination_remote(client, cb)
        else:
            # Finalize destination and confirm
            await conversation_state.update(cb.from_user.id, dst_path=base)
            await _rclone_cc_confirm_and_copy(client, cb)

async def _rclone_cc_pick_destination_remote(client, cb:CallbackQuery):
    # List remotes again for destination
    try:
        proc = await asyncio.create_subprocess_shell(
            'rclone listremotes --config ./rclone.conf | cat',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            return await edit_message(cb.message, f"Failed to list remotes:\n<code>{err.decode().strip()}</code>", markup=rclone_buttons())
        remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
        if not remotes:
            return await edit_message(cb.message, "No remotes configured.", markup=rclone_buttons())
        from ..helpers.state import conversation_state
        await conversation_state.set_stage(cb.from_user.id, 'rclone_cc_dest_remote')
        rows = [[InlineKeyboardButton(r, callback_data=f"rcloneCcPickDstRemote|{idx}")] for idx, r in enumerate(remotes[:25])]
        rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])
        await edit_message(cb.message, "Select DESTINATION remote:", InlineKeyboardMarkup(rows))
    except Exception as e:
        await edit_message(cb.message, f"Error: {e}", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcPickDstRemote\|"))
async def rclone_cc_pick_dst_remote(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        # Re-list remotes to map index
        proc = await asyncio.create_subprocess_shell(
            'rclone listremotes --config ./rclone.conf | cat',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
        if idx < 0 or idx >= len(remotes):
            return await _rclone_cc_pick_destination_remote(client, cb)
        dst_remote = remotes[idx]
        await conversation_state.update(cb.from_user.id, stage='rclone_cc_browse_dst', dst_remote=dst_remote, dst_path='')
        await _rclone_cc_render_browse(client, cb, which='dst', include_files=False)

async def _rclone_cc_confirm_and_copy(client, cb:CallbackQuery):
    from ..helpers.state import conversation_state
    state = await conversation_state.get(cb.from_user.id) or {}
    data = state.get('data', {})
    src_remote = data.get('src_remote')
    dst_remote = data.get('dst_remote')
    src_path = data.get('src_file') or data.get('src_path')
    dst_path = data.get('dst_path', '')
    mode = (data.get('cc_mode') or 'copy').lower()
    if not src_remote or not dst_remote or not src_path:
        return await edit_message(cb.message, "Missing source/destination selection.", rclone_buttons())
    src_full = f"{src_remote}:{src_path}"
    dst_full = f"{dst_remote}:{dst_path}" if dst_path else f"{dst_remote}:"
    verb = 'Move' if mode == 'move' else 'Copy'
    rows = [
        [InlineKeyboardButton(f"✅ Confirm {verb}", callback_data="rcloneCcDoCopy")],
        [InlineKeyboardButton("❌ Cancel", callback_data="rclonePanel")]
    ]
    text = (
        f"Cloud to Cloud {verb}\n\n"
        f"Source: <code>{src_full}</code>\n"
        f"Destination: <code>{dst_full}</code>\n\n"
        "Proceed?"
    )
    await edit_message(cb.message, text, InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcDoCopy$"))
async def rclone_cc_do_copy(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        src_remote = data.get('src_remote')
        dst_remote = data.get('dst_remote')
        src_path = data.get('src_file') or data.get('src_path')
        dst_path = data.get('dst_path', '')
        cfg = _get_rclone_config_arg()
        src_full = f"{src_remote}:{src_path}"
        dst_full = f"{dst_remote}:{dst_path}" if dst_path else f"{dst_remote}:"
        mode = (data.get('cc_mode') or 'copy').lower()
        cmd = 'move' if mode == 'move' else 'copy'
        # Start op
        try:
            await edit_message(cb.message, f"Starting {cmd}...\n<code>{src_full}</code> → <code>{dst_full}</code>")
            proc = await asyncio.create_subprocess_shell(
                f'rclone {cmd} {cfg} "{src_full}" "{dst_full}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                await edit_message(cb.message, f"✅ {cmd.capitalize()} completed successfully.", rclone_buttons())
            else:
                await edit_message(cb.message, f"❌ {cmd.capitalize()} failed:\n<code>{(err.decode().strip() or out.decode().strip())}</code>", rclone_buttons())
        except Exception as e:
            await edit_message(cb.message, f"❌ Error: {e}", rclone_buttons())

# Reuse existing helper to get rclone config arg
def _get_rclone_config_arg() -> str:
    import os
    from config import Config
    try:
        if getattr(Config, "RCLONE_CONFIG", None) and os.path.exists(Config.RCLONE_CONFIG):
            return f'--config "{Config.RCLONE_CONFIG}"'
    except Exception:
        pass
    for p in ("/workspace/rclone.conf", "rclone.conf"):
        try:
            if os.path.exists(p):
                return f'--config "{p}"'
        except Exception:
            continue
    return ""

@Client.on_callback_query(filters.regex(pattern=r"^rcloneCcPage\|"))
async def rclone_cc_page_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        try:
            _, which, page_str = cb.data.split('|', 2)
            new_page = int(page_str)
        except Exception:
            return
        await conversation_state.set_data(cb.from_user.id, f"{which}_page", new_page)
        await _rclone_cc_render_browse(client, cb, which=which, include_files=(which=='src'))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageStart$"))
async def rclone_manage_start_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        # Ensure we have src_remote/src_path or src_file
        if not data.get('src_remote'):
            return await edit_message(cb.message, "No uploaded item context found.", rclone_buttons())
        # Default to copy mode if not set
        mode = (data.get('cc_mode') or 'copy').lower()
        await _rclone_manage_render_source(client, cb, mode)

async def _rclone_manage_render_source(client, cb:CallbackQuery, mode: str):
    from ..helpers.state import conversation_state
    state = await conversation_state.get(cb.from_user.id) or {}
    data = state.get('data', {})
    src_remote = data.get('src_remote')
    base_path = data.get('src_path', '')
    include_files = True
    # List items at current base_path
    try:
        dirs, files = await _rclone_cc_list(src_remote, base_path, include_files)
    except Exception as e:
        return await edit_message(cb.message, f"Failed to list: {e}", rclone_buttons())
    await conversation_state.update(cb.from_user.id, **{'src_entries': {'dirs': dirs, 'files': files}})

    # Pagination
    PAGE_SIZE = 15
    page = int((data.get('src_page') or 0))
    combined = [("dir", name, i) for i, name in enumerate(dirs)] + [("file", name, i) for i, name in enumerate(files)]
    total = len(combined)
    max_page = 0 if total == 0 else (total - 1) // PAGE_SIZE
    if page < 0: page = 0
    if page > max_page: page = max_page
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []
    # Mode toggle row
    is_copy = (mode == 'copy')
    rows.append([
        InlineKeyboardButton(f"Copy {'✅' if is_copy else ''}", callback_data="rcloneManageMode|copy"),
        InlineKeyboardButton(f"Move {'✅' if not is_copy else ''}", callback_data="rcloneManageMode|move")
    ])

    for etype, name, idx in combined[start:end]:
        if etype == 'dir':
            rows.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"rcloneManageSrcCd|{idx}")])
        else:
            rows.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"rcloneManagePickFile|{idx}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"rcloneManageSrcPage|{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"rcloneManageSrcPage|{page+1}"))
    if nav:
        rows.append(nav)

    if base_path:
        rows.append([InlineKeyboardButton("⬆️ Up", callback_data="rcloneManageSrcUp")])
    rows.append([InlineKeyboardButton("Select this folder", callback_data="rcloneManageSelectFolder")])
    rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])

    title = f"Manage Uploaded • Source {src_remote}: /{base_path or ''}"
    await edit_message(cb.message, title, InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageMode\|"))
async def rclone_manage_mode_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        mode = cb.data.split('|', 1)[1]
        await conversation_state.set_data(cb.from_user.id, 'cc_mode', mode)
        await _rclone_manage_render_source(client, cb, mode)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageSrcPage\|"))
async def rclone_manage_src_page_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        try:
            page = int(cb.data.split('|', 1)[1])
        except Exception:
            return
        await conversation_state.set_data(cb.from_user.id, 'src_page', page)
        state = await conversation_state.get(cb.from_user.id) or {}
        mode = (state.get('data', {}).get('cc_mode') or 'copy')
        await _rclone_manage_render_source(client, cb, mode)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageSrcCd\|"))
async def rclone_manage_src_cd_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        entries = (data.get('src_entries') or {}).get('dirs') or []
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        if idx < 0 or idx >= len(entries):
            return await _rclone_manage_render_source(client, cb, (data.get('cc_mode') or 'copy'))
        base = data.get('src_path', '')
        new_path = f"{base}/{entries[idx]}" if base else entries[idx]
        await conversation_state.update(cb.from_user.id, src_path=new_path, src_page=0)
        await _rclone_manage_render_source(client, cb, (data.get('cc_mode') or 'copy'))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageSrcUp$"))
async def rclone_manage_src_up_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        base = data.get('src_path', '')
        parts = [p for p in base.split('/') if p]
        new_path = '/'.join(parts[:-1])
        await conversation_state.update(cb.from_user.id, src_path=new_path, src_page=0)
        await _rclone_manage_render_source(client, cb, (data.get('cc_mode') or 'copy'))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManagePickFile\|"))
async def rclone_manage_pick_file_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        files = (data.get('src_entries') or {}).get('files') or []
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        if idx < 0 or idx >= len(files):
            return await _rclone_manage_render_source(client, cb, (data.get('cc_mode') or 'copy'))
        base = data.get('src_path', '')
        choice = f"{base}/{files[idx]}" if base else files[idx]
        await conversation_state.update(cb.from_user.id, src_file=choice)
        await _rclone_manage_pick_destination_remote(client, cb)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageSelectFolder$"))
async def rclone_manage_select_folder_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        await conversation_state.update(cb.from_user.id, src_file=None)
        await _rclone_manage_pick_destination_remote(client, cb)

async def _rclone_manage_pick_destination_remote(client, cb:CallbackQuery):
    # list remotes
    try:
        proc = await asyncio.create_subprocess_shell(
            'rclone listremotes --config ./rclone.conf | cat',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            return await edit_message(cb.message, f"Failed to list remotes:\n<code>{err.decode().strip()}</code>", markup=rclone_buttons())
        remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
        if not remotes:
            return await edit_message(cb.message, "No remotes configured.", markup=rclone_buttons())
        rows = [[InlineKeyboardButton(r, callback_data=f"rcloneManagePickDstRemote|{i}")] for i, r in enumerate(remotes[:25])]
        rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])
        await edit_message(cb.message, "Select DESTINATION remote:", InlineKeyboardMarkup(rows))
    except Exception as e:
        await edit_message(cb.message, f"Error: {e}", markup=rclone_buttons())

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManagePickDstRemote\|"))
async def rclone_manage_pick_dst_remote_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        # map index to remotes
        proc = await asyncio.create_subprocess_shell(
            'rclone listremotes --config ./rclone.conf | cat',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        remotes = [r.strip(':') for r in out.decode().splitlines() if r.strip()]
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        if idx < 0 or idx >= len(remotes):
            return await _rclone_manage_pick_destination_remote(client, cb)
        dst_remote = remotes[idx]
        from ..helpers.state import conversation_state
        await conversation_state.set_data(cb.from_user.id, 'dst_remote', dst_remote)
        await _rclone_manage_render_dest(client, cb)

async def _rclone_manage_render_dest(client, cb:CallbackQuery):
    from ..helpers.state import conversation_state
    state = await conversation_state.get(cb.from_user.id) or {}
    data = state.get('data', {})
    dst_remote = data.get('dst_remote')
    base_path = data.get('dst_path', '')
    try:
        names = await _list_remote_dirs(dst_remote, base_path)
    except Exception as e:
        return await edit_message(cb.message, f"Failed to list folders: {e}", rclone_buttons())

    # pagination
    PAGE_SIZE = 15
    page = int((data.get('dst_page') or 0))
    total = len(names)
    max_page = 0 if total == 0 else (total - 1) // PAGE_SIZE
    if page < 0: page = 0
    if page > max_page: page = max_page
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []
    for i in range(start, end):
        rows.append([InlineKeyboardButton(names[i], callback_data=f"rcloneManageDstCd|{i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"rcloneManageDstPage|{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"rcloneManageDstPage|{page+1}"))
    if nav:
        rows.append(nav)

    if base_path:
        rows.append([InlineKeyboardButton("⬆️ Up", callback_data="rcloneManageDstUp")])
    rows.append([InlineKeyboardButton("Select here", callback_data="rcloneManageConfirm")])
    rows.append([InlineKeyboardButton("Cancel", callback_data="rclonePanel")])

    title = f"Destination {dst_remote}: /{base_path or ''}"
    await edit_message(cb.message, title, InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageDstPage\|"))
async def rclone_manage_dst_page_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        try:
            page = int(cb.data.split('|', 1)[1])
        except Exception:
            return
        await conversation_state.set_data(cb.from_user.id, 'dst_page', page)
        await _rclone_manage_render_dest(client, cb)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageDstCd\|"))
async def rclone_manage_dst_cd_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        entries = data.get('browse_entries') or []
        # We relist with indices each render; map by index into current page slice
        try:
            idx = int(cb.data.split('|', 1)[1])
        except Exception:
            idx = -1
        dst_remote = data.get('dst_remote')
        names = await _list_remote_dirs(dst_remote, data.get('dst_path',''))
        if idx < 0 or idx >= len(names):
            return await _rclone_manage_render_dest(client, cb)
        base = data.get('dst_path', '')
        new_path = f"{base}/{names[idx]}" if base else names[idx]
        await conversation_state.update(cb.from_user.id, dst_path=new_path, dst_page=0)
        await _rclone_manage_render_dest(client, cb)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageDstUp$"))
async def rclone_manage_dst_up_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        base = data.get('dst_path', '')
        parts = [p for p in base.split('/') if p]
        new_path = '/'.join(parts[:-1])
        await conversation_state.update(cb.from_user.id, dst_path=new_path, dst_page=0)
        await _rclone_manage_render_dest(client, cb)

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageConfirm$"))
async def rclone_manage_confirm_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        src_remote = data.get('src_remote')
        dst_remote = data.get('dst_remote')
        src_path = data.get('src_file') or data.get('src_path')
        dst_path = data.get('dst_path', '')
        if not src_remote or not dst_remote:
            return await edit_message(cb.message, "Missing source/destination.", rclone_buttons())
        src_full = f"{src_remote}:{src_path}"
        dst_full = f"{dst_remote}:{dst_path}" if dst_path else f"{dst_remote}:"
        mode = (data.get('cc_mode') or 'copy').lower()
        verb = 'Move' if mode == 'move' else 'Copy'
        rows = [
            [InlineKeyboardButton(f"✅ Proceed {verb}", callback_data="rcloneManageDo")],
            [InlineKeyboardButton("❌ Cancel", callback_data="rclonePanel")]
        ]
        await edit_message(cb.message, f"{verb} this item?\n\nFrom: <code>{src_full}</code>\nTo: <code>{dst_full}</code>", InlineKeyboardMarkup(rows))

@Client.on_callback_query(filters.regex(pattern=r"^rcloneManageDo$"))
async def rclone_manage_do_cb(client, cb:CallbackQuery):
    if await check_user(cb.from_user.id, restricted=True):
        from ..helpers.state import conversation_state
        state = await conversation_state.get(cb.from_user.id) or {}
        data = state.get('data', {})
        src_remote = data.get('src_remote')
        dst_remote = data.get('dst_remote')
        src_path = data.get('src_file') or data.get('src_path')
        dst_path = data.get('dst_path', '')
        cfg = _get_rclone_config_arg()
        if not src_remote or not dst_remote or not src_path:
            return await edit_message(cb.message, "Missing source/destination selection.", rclone_buttons())
        src_full = f"{src_remote}:{src_path}"
        dst_full = f"{dst_remote}:{dst_path}" if dst_path else f"{dst_remote}:"
        mode = (data.get('cc_mode') or 'copy').lower()
        cmd = 'move' if mode == 'move' else 'copy'
        try:
            await edit_message(cb.message, f"Starting {cmd}...\n<code>{src_full}</code> → <code>{dst_full}</code>")
            proc = await asyncio.create_subprocess_shell(
                f'rclone {cmd} {cfg} "{src_full}" "{dst_full}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                await edit_message(cb.message, f"✅ {cmd.capitalize()} completed successfully.", rclone_buttons())
            else:
                await edit_message(cb.message, f"❌ {cmd.capitalize()} failed:\n<code>{(err.decode().strip() or out.decode().strip())}</code>", rclone_buttons())
        except Exception as e:
            await edit_message(cb.message, f"❌ Error: {e}", rclone_buttons())
