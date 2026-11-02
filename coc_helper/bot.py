"""NoneBot2 plugin: /战况 /成员 /统计 /报表 /战绩 /帮助."""

from __future__ import annotations

import asyncio
import base64

from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg

from .api import CocApiError, CocClient
from .config import load_settings
from .render import (
    format_attacks,
    format_history_lines,
    format_members_lines,
    format_recent_wars,
    format_summary,
    format_war,
)
from .render_image import render_history_image, render_war_image
from .store import Store
from .tracker import track_loop

_settings = load_settings()
_client = CocClient(_settings.token)

war_cmd = on_command("战况", aliases={"war"}, priority=5, block=True)
members_cmd = on_command("成员", aliases={"members"}, priority=5, block=True)
stats_cmd = on_command("统计", aliases={"stats"}, priority=5, block=True)
detail_cmd = on_command("详情", aliases={"进攻", "attacks"}, priority=5, block=True)
report_cmd = on_command("报表", aliases={"history", "赛季"}, priority=5, block=True)
recent_cmd = on_command("战绩", aliases={"wars"}, priority=5, block=True)
help_cmd = on_command("帮助", aliases={"help"}, priority=5, block=True)

_tracker_started = False


@get_driver().on_startup
async def _start_tracker() -> None:
    global _tracker_started
    if _tracker_started:
        return
    _tracker_started = True
    asyncio.create_task(track_loop())


async def _current():
    return await asyncio.to_thread(_client.find_current_war, _settings.clan_tag)


def _save(result) -> None:
    store = Store(_settings.db_path)
    try:
        store.upsert_war(_settings.clan_tag, result)
    finally:
        store.close()


async def _current_and_save():
    result = await _current()
    if result:
        await asyncio.to_thread(_save, result)
    return result


def _history_rows(limit: int):
    store = Store(_settings.db_path)
    try:
        return store.member_history(_settings.clan_tag, limit)
    finally:
        store.close()


def _recent_rows(limit: int):
    store = Store(_settings.db_path)
    try:
        return store.recent_wars(_settings.clan_tag, limit)
    finally:
        store.close()


def _clan_name() -> str:
    try:
        return _client.get_clan(_settings.clan_tag).get("name") or _settings.clan_tag
    except CocApiError:
        return _settings.clan_tag


@war_cmd.handle()
async def _war():
    try:
        result = await _current_and_save()
    except CocApiError as exc:
        await war_cmd.finish(f"API 错误: {exc}")
    if not result:
        await war_cmd.finish("当前没有进行中的部落战/联赛。")

    try:
        png = await asyncio.to_thread(render_war_image, result)
    except Exception:
        logger.exception("render_war_image failed; falling back to text")
        await war_cmd.finish(format_war(result))

    b64 = base64.b64encode(png).decode("ascii")
    await war_cmd.finish(MessageSegment.image(f"base64://{b64}"))


@members_cmd.handle()
async def _members():
    try:
        result = await _current_and_save()
    except CocApiError as exc:
        await members_cmd.finish(f"API 错误: {exc}")
    if not result:
        await members_cmd.finish("当前没有进行中的部落战/联赛。")
    await members_cmd.finish(format_members_lines(result))


@stats_cmd.handle()
async def _stats():
    try:
        result = await _current_and_save()
    except CocApiError as exc:
        await stats_cmd.finish(f"API 错误: {exc}")
    if not result:
        await stats_cmd.finish("当前没有进行中的部落战/联赛。")
    await stats_cmd.finish(format_summary(result))


@detail_cmd.handle()
async def _detail():
    try:
        result = await _current_and_save()
    except CocApiError as exc:
        await detail_cmd.finish(f"API 错误: {exc}")
    if not result:
        await detail_cmd.finish("当前没有进行中的部落战/联赛。")
    await detail_cmd.finish(format_attacks(result))


@report_cmd.handle()
async def _report(args: Message = CommandArg()):
    limit = 20
    text = args.extract_plain_text().strip()
    if text.isdigit():
        limit = max(1, min(int(text), 50))

    rows = await asyncio.to_thread(_history_rows, limit)
    if not rows:
        await report_cmd.finish(
            "还没有已结束的战争。等这场 CWL 打完，bot 存下来后就能看报表。"
        )

    clan_name = await asyncio.to_thread(_clan_name)
    try:
        png = await asyncio.to_thread(render_history_image, clan_name, rows, limit)
    except Exception:
        logger.exception("render_history_image failed; falling back to text")
        await report_cmd.finish(format_history_lines(rows))

    b64 = base64.b64encode(png).decode("ascii")
    await report_cmd.finish(MessageSegment.image(f"base64://{b64}"))


@recent_cmd.handle()
async def _recent():
    rows = await asyncio.to_thread(_recent_rows, 10)
    await recent_cmd.finish(format_recent_wars(rows))


@help_cmd.handle()
async def _help():
    await help_cmd.finish(
        "COC 部落战查询\n"
        "/战况  - 图片战报（成员表）\n"
        "/成员  - 一人一行文字版\n"
        "/统计  - 总星/三星率/平均摧毁\n"
        "/详情  - 对方成员 + 每次进攻明细\n"
        "/报表 [N] - 最近 N 场历史统计（图片）\n"
        "/战绩  - 最近 10 场胜负\n"
        "/帮助  - 本菜单"
    )
