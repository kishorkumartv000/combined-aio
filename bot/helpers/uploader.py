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
from bot.settings import bot_set
from bot.helpers.progress import ProgressReporter

async def track_upload(metadata, user, index: int = None, total: int = None):
    """
    Upload a single track
    Args:
        metadata: Track metadata
        user: User details
        index: Optional file index for progress display
        total: Optional total files for progress display
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['filepath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, str(user['user_id']), "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        reporter = user.get('progress')
        if reporter:
            await reporter.set_stage("Uploading")
        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                "🎵 **{title}**\n👤 {artist}\n🎧 {provider}",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            ),
            meta={
                'duration': metadata['duration'],
                'artist': metadata['artist'],
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail']
            },
            progress_reporter=reporter,
            progress_label="Uploading",
            file_index=index,
            total_files=total
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def music_video_upload(metadata, user):
    """
    Upload a music video
    Args:
        metadata: Video metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['filepath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, str(user['user_id']), "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        reporter = user.get('progress')
        if reporter:
            await reporter.set_stage("Uploading")
        # FIX: Pass the entire metadata object as meta parameter
        await send_message(
            user,
            metadata['filepath'],
            'video',
            caption=await format_string(
                "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            ),
            meta=metadata,  # PASS METADATA HERE
            progress_reporter=reporter,
            progress_label="Uploading",
            file_index=1,
            total_files=1
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def album_upload(metadata, user):
    """
    Upload an album
    Args:
        metadata: Album metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, str(user['user_id']), "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        reporter = user.get('progress')
        if Config.ALBUM_ZIP:
            # Create descriptive zip file
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata,
                progress=reporter
            )
            
            # Create caption with provider info
            caption = await format_string(
                "💿 **{album}**\n👤 {artist}\n🎧 {provider}",
                {
                    'album': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption,
                progress_reporter=reporter,
                progress_label="Uploading",
                file_index=1,
                total_files=1
            )
            
            # Clean up zip file after upload
            os.remove(zip_path)
        else:
            # Upload tracks individually
            tracks = metadata.get('tracks', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'album': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
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
    """
    Upload an artist's content
    Args:
        metadata: Artist metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, str(user['user_id']), "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        reporter = user.get('progress')
        if Config.ARTIST_ZIP:
            # Create descriptive zip file
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata,
                progress=reporter
            )
            
            # Create caption with provider info
            caption = await format_string(
                "🎤 **{artist}**\n🎧 {provider} Discography",
                {
                    'artist': metadata['title'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption,
                progress_reporter=reporter,
                progress_label="Uploading",
                file_index=1,
                total_files=1
            )
            
            # Clean up zip file after upload
            os.remove(zip_path)
        else:
            # Upload albums individually
            for album in metadata['albums']:
                await album_upload(album, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎤 **{artist}**\n🎧 {provider} Discography\n🔗 [Direct Link]({r_link})",
            {
                'artist': metadata['title'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    shutil.rmtree(metadata['folderpath'])

async def playlist_upload(metadata, user):
    """
    Upload a playlist
    Args:
        metadata: Playlist metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, str(user['user_id']), "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        reporter = user.get('progress')
        if Config.PLAYLIST_ZIP:
            # Create descriptive zip file
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata,
                progress=reporter
            )
            
            # Create caption with provider info
            caption = await format_string(
                "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist",
                {
                    'title': metadata['title'],
                    'artist': metadata.get('artist', 'Various Artists'),
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption,
                progress_reporter=reporter,
                progress_label="Uploading",
                file_index=1,
                total_files=1
            )
            
            # Clean up zip file after upload
            os.remove(zip_path)
        else:
            # Upload tracks individually
            tracks = metadata.get('tracks', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata.get('artist', 'Various Artists'),
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    shutil.rmtree(metadata['folderpath'])

async def rclone_upload(user, path, base_path):
    """
    Upload files via Rclone
    Args:
        user: User details
        path: Path to file/folder
        base_path: Base directory path
    Returns:
        rclone_link, index_link
    """
    # Skip if not configured
    if not Config.RCLONE_DEST:
        return None, None
    
    # Get relative path
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
