import os
import shutil
import zipfile
import asyncio
from config import Config
from bot.helpers.utils import create_apple_zip, format_string, send_message, edit_message
from bot.logger import LOGGER
from mutagen import File
from mutagen.mp4 import MP4

async def track_upload(metadata, user):
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
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'])
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
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'])
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

async def rclone_upload(user, path):
    """Rclone upload implementation would go here"""
    return "rclone_link", "index_link"
