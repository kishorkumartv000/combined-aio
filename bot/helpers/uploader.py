import os
import shutil
import zipfile
import asyncio
from config import Config
from bot.helpers.utils import create_apple_zip, format_string, send_message, edit_message
from bot.logger import LOGGER
from mutagen import File
from mutagen.mp4 import MP4
import re

async def track_upload(metadata, user):
    # Determine base path for different providers
    if "Apple Music" in metadata['filepath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                f"🎵 **{{title}}**\n👤 {{artist}}",
                metadata
            ),
            meta={
                'duration': metadata['duration'],
                'artist': metadata['artist'],
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail']
            }
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🔗 [Direct Link]({r_link})",
            {**metadata, 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def album_upload(metadata, user):
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.ALBUM_ZIP:
            zip_path = await create_apple_zip(metadata['folderpath'], user['user_id'])
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "💿 **{album}**\n👤 {artist}",
                    {
                        'album': metadata['title'],
                        'artist': metadata['artist']
                    }
                )
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await track_upload(track, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🔗 [Direct Link]({r_link})",
            {
                'album': metadata['title'],
                'artist': metadata['artist'],
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        
        if metadata.get('poster_msg'):
            await edit_message(metadata['poster_msg'], text)
        else:
            await send_message(user, text)
    
    # Cleanup
    shutil.rmtree(metadata['folderpath'])

async def artist_upload(metadata, user):
    """Placeholder for artist upload functionality"""
    await send_message(
        user,
        f"🎤 Artist download would process: {metadata['title']}",
        'text'
    )

async def playlist_upload(metadata, user):
    """Placeholder for playlist upload functionality"""
    await send_message(
        user,
        f"🎵 Playlist download would process: {metadata['title']}",
        'text'
    )

async def rclone_upload(user, path, base_path):
    """Rclone upload implementation with proper path handling"""
    # Skip RCLONE link generation if not configured
    if not Config.RCLONE_DEST:
        return None, None
    
    # Get relative path for Rclone
    relative_path = str(path).replace(base_path, "").lstrip('/')
    
    rclone_link = None
    index_link = None

    if bot_set.link_options in ['RCLONE', 'Both']:
        cmd = f'rclone link --config ./rclone.conf "{Config.RCLONE_DEST}/{relative_path}"'
        task = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await task.communicate()

        if task.returncode == 0:
            rclone_link = stdout.decode().strip()
        else:
            error_message = stderr.decode().strip()
            LOGGER.debug(f"Failed to get Rclone link: {error_message}")
    
    if bot_set.link_options in ['Index', 'Both']:
        if Config.INDEX_LINK:
            index_link = f"{Config.INDEX_LINK}/{relative_path}"
    
    return rclone_link, index_link
