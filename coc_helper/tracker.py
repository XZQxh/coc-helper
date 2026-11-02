"""Background war tracker: poll the current war and persist snapshots."""

from __future__ import annotations

import asyncio

from nonebot.log import logger

from .api import CocApiError, CocClient
from .config import load_settings
from .store import Store


async def track_loop() -> None:
    settings = load_settings()
    client = CocClient(settings.token)
    logger.info("war tracker started")

    while True:
        try:
            result = await asyncio.to_thread(
                client.find_current_war, settings.clan_tag
            )
            if result:
                await asyncio.to_thread(_save, settings, result)
                interval = 60 if result.war.get("state") == "inWar" else 300
            else:
                interval = 300
        except CocApiError as exc:
            logger.warning(f"war tracker API error: {exc}")
            interval = 300
        except Exception:
            logger.exception("war tracker failed")
            interval = 300
        await asyncio.sleep(interval)


def _save(settings, result) -> None:
    store = Store(settings.db_path)
    try:
        store.upsert_war(settings.clan_tag, result)
    finally:
        store.close()
