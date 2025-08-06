from config import Config
import bot.helpers.translations as lang
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def links_button(rclone, index):
    inline_keyboard = []
    if rclone:
        inline_keyboard.append([
            InlineKeyboardButton(lang.s.RCLONE_LINK, url=rclone)
        ])
    if index:
        inline_keyboard.append([
            InlineKeyboardButton(lang.s.INDEX_LINK, url=index)
        ])
    if not inline_keyboard:
        return None
    return InlineKeyboardMarkup(inline_keyboard)
