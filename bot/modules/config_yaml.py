from __future__ import annotations

import os
import shutil
import time
from typing import Any

from pyrogram import Client, filters
from pyrogram.types import Message

from config import Config
from ..helpers.message import send_message, check_user

YAML_PATH = Config.APPLE_CONFIG_YAML_PATH

SENSITIVE_KEYS = {"media-user-token", "authorization-token"}


def _read_yaml_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def _write_yaml_lines(path: str, lines: list[str]) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    # atomic replace
    os.replace(tmp_path, path)


def _backup(path: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_path = f"{path}.bak.{ts}"
    try:
        shutil.copy2(path, backup_path)
    except Exception:
        pass
    return backup_path


def _mask_value(key: str, value: str) -> str:
    if key in SENSITIVE_KEYS and value:
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    return value


def _parse_kv(line: str) -> tuple[str | None, str | None]:
    s = line.strip()
    if not s or s.startswith("#") or ":" not in s:
        return None, None
    key, rest = s.split(":", 1)
    return key.strip(), rest.strip()


def _set_key(lines: list[str], key: str, raw_value: str) -> list[str]:
    quote = '"' if raw_value.startswith('"') and raw_value.endswith('"') else None
    value = raw_value
    found = False
    new_lines: list[str] = []
    for ln in lines:
        k, _ = _parse_kv(ln)
        if k and k.lower() == key.lower():
            found = True
            # preserve inline comment if present
            comment = ""
            if "#" in ln:
                comment = " " + ln.split("#", 1)[1].rstrip("\n")
            # keep quotes if original had them or incoming has them
            if value and not (value.startswith('"') or value.startswith("'")) and any(ch in value for ch in [":", "#", " "]):
                value_fmt = f'"{value}"'
            else:
                value_fmt = value
            new_lines.append(f"{key}: {value_fmt}{comment}\n")
        else:
            new_lines.append(ln)
    if not found:
        if value and not (value.startswith('"') or value.startswith("'")) and any(ch in value for ch in [":", "#", " "]):
            value_fmt = f'"{value}"'
        else:
            value_fmt = value
        new_lines.append(f"{key}: {value_fmt}\n")
    return new_lines


def _get_key(lines: list[str], key: str) -> str | None:
    for ln in lines:
        k, v = _parse_kv(ln)
        if k and k.lower() == key.lower():
            # strip inline comment
            if v is None:
                return None
            val = v.split("#", 1)[0].strip()
            return val
    return None


@Client.on_message(filters.command(["config", "cfg"]))
async def config_help(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    text = (
        "Apple Music YAML config control\n\n"
        "Usage:\n"
        "- /config_get <key>\n"
        "- /config_set <key> <value>\n"
        "- /config_show [keys...] (space-separated)\n"
        f"Path: {YAML_PATH}"
    )
    await send_message(msg, text)


@Client.on_message(filters.command(["config_get"]))
async def config_get(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await send_message(msg, "Usage: /config_get <key>")
        return
    key = parts[1].strip()
    lines = _read_yaml_lines(YAML_PATH)
    val = _get_key(lines, key)
    if val is None:
        await send_message(msg, f"{key}: <not set>")
    else:
        shown = _mask_value(key, val.strip('"'))
        await send_message(msg, f"{key}: {shown}")


@Client.on_message(filters.command(["config_set"]))
async def config_set(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await send_message(msg, "Usage: /config_set <key> <value>")
        return
    key = parts[1].strip()
    value = parts[2].strip()

    if key in SENSITIVE_KEYS and not (value.startswith('"') or value.startswith("'")):
        # wrap sensitive values in quotes to avoid YAML parsing issues
        value = f'"{value}"'

    lines = _read_yaml_lines(YAML_PATH)
    if not lines:
        # create file if absent
        _write_yaml_lines(YAML_PATH, [])
        lines = []
    _backup(YAML_PATH)
    new_lines = _set_key(lines, key, value)
    try:
        _write_yaml_lines(YAML_PATH, new_lines)
    except Exception as e:
        await send_message(msg, f"Failed to write config: {e}")
        return

    if key.lower().endswith("-save-folder"):
        try:
            os.makedirs(value.strip('"'), exist_ok=True)
        except Exception:
            pass

    await send_message(msg, f"Updated {key}.")


@Client.on_message(filters.command(["config_show"]))
async def config_show(c: Client, msg: Message):
    if not await check_user(msg.from_user.id, restricted=True):
        return
    lines = _read_yaml_lines(YAML_PATH)
    keys = msg.text.split()[1:]
    rows: list[str] = []
    if keys:
        for k in keys:
            v = _get_key(lines, k)
            v_shown = _mask_value(k, (v or "").strip('"')) if v is not None else "<not set>"
            rows.append(f"- {k}: {v_shown}")
    else:
        # show a curated list
        interesting = [
            "media-user-token",
            "authorization-token",
            "language",
            "lrc-type",
            "lrc-format",
            "embed-lrc",
            "save-lrc-file",
            "save-artist-cover",
            "save-animated-artwork",
            "emby-animated-artwork",
            "embed-cover",
            "cover-size",
            "cover-format",
            "alac-save-folder",
            "atmos-save-folder",
            "aac-save-folder",
            "alac-max",
            "atmos-max",
            "aac-type",
            "storefront",
        ]
        for k in interesting:
            v = _get_key(lines, k)
            v_shown = _mask_value(k, (v or "").strip('"')) if v is not None else "<not set>"
            rows.append(f"- {k}: {v_shown}")
    out = "\n".join(rows) or "No keys."
    await send_message(msg, out)