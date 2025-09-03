from ..message import send_message

async def start_tidal_ng(link: str, user: dict):
    """
    Placeholder handler for the new Tidal DL NG provider.
    """
    await send_message(
        user,
        "⚙️ **Tidal DL NG Provider**\n\nThis provider is currently under development. "
        "It will be used automatically when the Legacy Tidal provider is disabled."
    )
