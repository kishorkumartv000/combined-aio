import os
import math
import aiohttp
import asyncio
import shutil
import zipfile
import re
import subprocess
import mutagen
from mutagen.mp4 import MP4
from pathlib import Path
from urllib.parse import quote
from aiohttp import ClientTimeout
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait

from config import Config
import bot.helpers.translations as lang

from ..logger import LOGGER
from ..settings import bot_set
from .buttons.links import links_button
from .message import send_message, edit_message

MAX_SIZE = 1.9 * 1024 * 1024 * 1024  # 2GB
# download folder structure : BASE_DOWNLOAD_DIR + message_r_id

async def download_file(url, path, retries=3, timeout=30):
    """
    Args:
        url (str): URL to download.
        path (str): Path including filename with extension.
        retries (int): Number of retries in case of failure.
        timeout (int): Timeout duration for the request in seconds.
    Returns:
        str or None: Error message if any, else None.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(1024 * 4):
                                f.write(chunk)
                        return None
                    else:
                        return f"HTTP Status: {response.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == retries:
                return f"Failed after {retries} attempts: {str(e)}"
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            return f"Unexpected error: {str(e)}"


async def format_string(text:str, data:dict, user=None):
    """
    Args:
        text: text to be formatted
        data: source info
        user: user details
    Returns:
        str
    """
    replacements = {
        '{title}': data.get('title', ''),
        '{album}': data.get('album', ''),
        '{artist}': data.get('artist', ''),
        '{albumartist}': data.get('albumartist', ''),
        '{tracknumber}': str(data.get('tracknumber', '')),
        '{date}': str(data.get('date', '')),
        '{upc}': str(data.get('upc', '')),
        '{isrc}': str(data.get('isrc', '')),
        '{totaltracks}': str(data.get('totaltracks', '')),
        '{volume}': str(data.get('volume', '')),
        '{totalvolume}': str(data.get('totalvolume', '')),
        '{extension}': data.get('extension', ''),
        '{duration}': str(data.get('duration', '')),
        '{copyright}': data.get('copyright', ''),
        '{genre}': data.get('genre', ''),
        '{provider}': data.get('provider', '').title(),
        '{quality}': data.get('quality', ''),
        '{explicit}': str(data.get('explicit', '')),
    }
    
    if user:
        replacements['{user}'] = user.get('name', '')
        replacements['{username}'] = user.get('user_name', '')
    
    for key, value in replacements.items():
        text = text.replace(key, value)
        
    return text


async def run_concurrent_tasks(tasks, progress_details=None):
    """
    Args:
        tasks: (list) async functions to be run
        progress_details: details for progress message (dict)    
    """
    semaphore = asyncio.Semaphore(Config.MAX_WORKERS)
    completed = 0
    total = len(tasks)
    
    async def run_task(task):
        nonlocal completed
        async with semaphore:
            result = await task
            completed += 1
            if progress_details:
                progress = int((completed / total) * 100)
                try:
                    await edit_message(
                        progress_details['msg'],
                        f"{progress_details['text']}\nProgress: {progress}%"
                    )
                except FloodWait:
                    pass
            return result
            
    return await asyncio.gather(*(run_task(task) for task in tasks))


async def create_link(path, basepath):
    """
    Creates rclone and index link
    Args:
        path: full real path
        basepath: to remove bot folder from real path (DOWNLOADS/r_id/)
    Returns:
        rclone_link: link from rclone
        index_link: index link if enabled
    """
    path = str(Path(path).relative_to(basepath))

    rclone_link = None
    index_link = None

    if bot_set.link_options == 'RCLONE' or bot_set.link_options=='Both':
        cmd = f'rclone link --config ./rclone.conf "{Config.RCLONE_DEST}/{path}"'
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
            LOGGER.debug(f"Failed to get link: {error_message}")
    if bot_set.link_options == 'Index' or bot_set.link_options=='Both':
        if Config.INDEX_LINK:
            index_link =  Config.INDEX_LINK + '/' + quote(path)

    return rclone_link, index_link


async def zip_handler(folderpath):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        if bot_set.upload_mode == 'Telegram':
            zips = await loop.run_in_executor(pool, split_zip_folder, folderpath)
        else:
            zips = await loop.run_in_executor(pool, zip_folder, folderpath)
        return zips


def split_zip_folder(folderpath) -> list:
    """
    Args:
        folderpath: path to folder to zip
    Returns:
        list of zip file paths
    """
    zip_paths = []
    part_num = 1
    current_size = 0
    current_files = []

    def add_to_zip(zip_name, files_to_add):
        if part_num == 1:
            zip_path = f"{zip_name}.zip"
        else:
            zip_path = f"{zip_name}.part{part_num}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, arcname in files_to_add:
                zipf.write(file_path, arcname)
                os.remove(file_path)  # Delete the file after zipping
        return zip_path

    for root, dirs, files in os.walk(folderpath):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            arcname = os.path.relpath(file_path, folderpath)

            # If adding this file would exceed the max size, create a zip for the current files
            if current_size + file_size > MAX_SIZE:
                zip_paths.append(add_to_zip(folderpath, current_files))
                part_num += 1
                current_files = []  # Reset for the next zip part
                current_size = 0

            # Add the file to the current group
            current_files.append((file_path, arcname))
            current_size += file_size

    # Create the final zip with any remaining files
    if current_files:
        zip_paths.append(add_to_zip(folderpath, current_files))

    return zip_paths


def zip_folder(folderpath) -> str:
    """
    Args:
        folderpath (str): The path of the folder to zip.
    Returns:
        str: The path to the created zip file.
    """
    zip_path = f"{folderpath}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folderpath):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folderpath))
                # Remove file after adding to the zip
                os.remove(file_path)
    
    return zip_path


async def move_sorted_playlist(metadata, user) -> str:
    """
    Moves the sorted playlist files into a new playlist folder.
    Used since sorted tracks doest belong to a specific palylist folder
    Returns:
        str: path to the newly created playlist folder
    """

    source_folder = f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}/{metadata['provider']}"
    destination_folder = f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}/{metadata['provider']}/{metadata['title']}"

    os.makedirs(destination_folder, exist_ok=True)

    # get list of folders inside the source
    folders = [
        os.path.join(source_folder, name) for name in os.listdir(source_folder) if os.path.isdir(os.path.join(source_folder, name))
    ]

    for folder in folders:
        shutil.move(folder, destination_folder)

    return destination_folder


async def post_art_poster(user:dict, meta:dict):
    """
    Args:
        markup: buttons if needed
    Returns:
        Message
    """
    photo = meta['cover']
    if meta['type'] == 'album':
        caption = await format_string(lang.s.ALBUM_TEMPLATE, meta, user)
    else:
        caption = await format_string(lang.s.PLAYLIST_TEMPLATE, meta, user)
    
    if bot_set.art_poster:
        msg = await send_message(user, photo, 'pic', caption)
        return msg


async def create_simple_text(meta, user):
    caption = await format_string(
        lang.s.SIMPLE_TITLE.format(
            meta['title'],
            meta['type'].title(),
            meta['provider']
        ), 
        meta, 
        user
    )
    return caption


async def edit_art_poster(metadata, user, r_link, i_link, caption):
    """
    Edits Album/Playlist Art Poster with given information
    Args:
        metadata: metadata dict of item
        caption: text to edit
    """
    markup = links_button(r_link, i_link)
    await edit_message(
        metadata['poster_msg'],
        caption,
        markup
    )


async def post_simple_message(user, meta, r_link=None, i_link=None):
    """
    Sends a simple message of item with button
    Args:
        user: user details
        meta: metadata
        markup: buttons if needed
    Returns:
        Message
    """
    caption = await create_simple_text(meta, user)
    markup = links_button(r_link, i_link)
    await send_message(user, caption, markup=markup)


async def progress_message(done, total, details):
    """
    Args:
        done: how much task done
        total: total number of tasks
        details: Message, text (dict)
    """
    progress_bar = "{0}{1}".format(
        ''.join(["▰" for i in range(math.floor((done/total) * 10))),
        ''.join(["▱" for i in range(10 - math.floor((done/total) * 10))])
    )

    try:
        await edit_message(
            details['msg'],
            details['text'].format(
                progress_bar, 
                done, 
                total, 
                details['title'],
                details['type'].title()
            ),
            None,
            False
        )
    except FloodWait as e:
        pass # dont update the message if flooded


async def cleanup(user=None, metadata=None, ):
    """
    Clean up after task completed - For concurrent downloads
    Clean up after upload - For single download
    
    if metadata
        Artist/Album/Playlist files are deleted
    if user
        user root folder is removed
    
    """
    if metadata:
        try:
            if metadata['type'] == 'album':
                is_zip = True if bot_set.album_zip else False
            elif metadata['type'] == 'artist':
                is_zip = True if bot_set.artist_zip else False
            else:
                is_zip = True if bot_set.playlist_zip else False
            if is_zip:
                if type(metadata['folderpath']) == list:
                    for i in metadata['folderpath']:
                        os.remove(i)
                else:
                    os.remove(metadata['folderpath'])
            else:
                shutil.rmtree(metadata['folderpath'])
        except FileNotFoundError:
            pass
    if user:
        try:
            shutil.rmtree(f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}/")
        except Exception as e:
            LOGGER.info(e)
        try:
            shutil.rmtree(f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}-temp/")
        except Exception as e:
            LOGGER.info(e)

# Apple Music specific utilities
async def run_apple_downloader(url: str, output_dir: str, options: list = None) -> dict:
    """
    Execute Apple Music downloader script with customizable options
    
    Args:
        url: Apple Music URL to download
        output_dir: Directory to save downloaded files
        options: List of additional command-line options
        
    Returns:
        dict: {'success': bool, 'error': str if failed}
    """
    cmd = [Config.DOWNLOADER_PATH]
    
    # Add options if provided
    if options:
        cmd.extend(options)
    
    # Add URL
    cmd.append(url)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=output_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error = stderr.decode().strip() or stdout.decode().strip()
        return {'success': False, 'error': error}
    
    return {'success': True}


async def extract_apple_metadata(file_path: str) -> dict:
    try:
        if file_path.endswith('.m4a'):
            audio = MP4(file_path)
            return {
                'title': audio.get('\xa9nam', ['Unknown'])[0],
                'artist': audio.get('\xa9ART', ['Unknown Artist'])[0],
                'album': audio.get('\xa9alb', ['Unknown Album'])[0],
                'duration': int(audio.info.length),
                'thumbnail': extract_cover_art(audio, file_path)
            }
        else:
            audio = mutagen.File(file_path)
            return {
                'title': audio.get('title', ['Unknown'])[0],
                'artist': audio.get('artist', ['Unknown Artist'])[0],
                'album': audio.get('album', ['Unknown Album'])[0],
                'duration': int(audio.info.length),
                'thumbnail': None
            }
    except Exception as e:
        LOGGER.error(f"Metadata extraction failed: {str(e)}")
        return default_metadata(file_path)


def extract_cover_art(audio, file_path):
    """Extract cover art from audio file"""
    if 'covr' in audio:
        cover_data = audio['covr'][0]
        cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
        try:
            with open(cover_path, 'wb') as f:
                f.write(cover_data)
            return cover_path
        except Exception as e:
            LOGGER.error(f"Failed to save cover art: {str(e)}")
    return None


def default_metadata(file_path):
    """Return default metadata when extraction fails"""
    return {
        'title': os.path.splitext(os.path.basename(file_path))[0],
        'artist': 'Unknown Artist',
        'album': 'Unknown Album',
        'duration': 0,
        'thumbnail': None
    }


async def create_apple_zip(directory: str, user_id: int) -> str:
    """Create zip file for Apple Music downloads"""
    zip_path = os.path.join(Config.LOCAL_STORAGE, f"apple_{user_id}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory)
                zipf.write(file_path, arcname)
    
    return zip_path
