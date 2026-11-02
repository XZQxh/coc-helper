"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
import time

from .api import CocApiError, CocClient, WarResult
from .config import load_settings
from .render import format_history_lines, format_recent_wars, format_war
from .store import Store


def print_war(result: WarResult, save: bool) -> None:
    print(format_war(result))
    if not save:
        return

    settings = load_settings()
    store = Store(settings.db_path)
    try:
        client = CocClient(settings.token)
        try:
            store.upsert_clan(client.get_clan(settings.clan_tag))
        except CocApiError:
            pass
        key = store.upsert_war(settings.clan_tag, result)
        print(f"\n已保存: {settings.db_path} (war_key={key})")
    finally:
        store.close()


def cmd_verify(_args: argparse.Namespace) -> int:
    settings = load_settings()
    client = CocClient(settings.token)
    clan = client.get_clan(settings.clan_tag)
    print(
        f"clan: {clan.get('name')} {clan.get('tag')} "
        f"level={clan.get('clanLevel')} members={len(clan.get('memberList') or [])}"
    )

    try:
        result = client.find_current_war(settings.clan_tag)
    except CocApiError as exc:
        print(f"war: error {exc}")
        result = None
    if result:
        print(
            f"war: {result.kind} state={result.war.get('state')} "
            f"team={result.war.get('teamSize')} tag={result.war_tag} side={result.our_side}"
        )
    else:
        print("war: none")

    try:
        log = client.get_warlog(settings.clan_tag)
        print(f"warlog: {len(log.get('items') or [])} items")
    except CocApiError as exc:
        print(f"warlog: {exc.status} {exc.reason} (private?)")
    return 0


def cmd_war(args: argparse.Namespace) -> int:
    settings = load_settings()
    client = CocClient(settings.token)
    try:
        result = client.find_current_war(settings.clan_tag)
    except CocApiError as exc:
        print(f"API 错误: {exc}", file=sys.stderr)
        return 2
    if not result:
        print("当前没有进行中的部落战/联赛。")
        return 0
    print_war(result, args.save)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    settings = load_settings()
    client = CocClient(settings.token)
    last: str | None = None

    while True:
        try:
            result = client.find_current_war(settings.clan_tag)
        except CocApiError as exc:
            print(f"[{time.strftime('%H:%M:%S')}] API 错误: {exc}")
            result = None

        if result:
            snapshot = json.dumps(result.war, sort_keys=True)
            if snapshot != last:
                print(f"\n[{time.strftime('%H:%M:%S')}] 状态变化")
                print_war(result, args.save)
                last = snapshot
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 无变化")
            state = result.war.get("state")
            interval = settings.poll_war if state == "inWar" else settings.poll_prep
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 当前没有进行中的部落战/联赛")
            interval = settings.poll_prep

        if args.once:
            return 0
        time.sleep(interval)


def cmd_history(args: argparse.Namespace) -> int:
    settings = load_settings()
    store = Store(settings.db_path)
    try:
        rows = store.member_history(settings.clan_tag, args.limit)
        print(format_history_lines(rows))
        print()
        print(format_recent_wars(store.recent_wars(settings.clan_tag, args.limit)))
    finally:
        store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coc-helper")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="验证 API、部落、战争日志与 CWL")
    verify.set_defaults(func=cmd_verify)

    war = sub.add_parser("war", help="打印当前战争/联赛战况")
    war.add_argument("--save", action="store_true", help="写入 SQLite")
    war.set_defaults(func=cmd_war)

    watch = sub.add_parser("watch", help="轮询并在状态变化时打印")
    watch.add_argument("--save", action="store_true", help="写入 SQLite")
    watch.add_argument("--once", action="store_true", help="只轮询一次")
    watch.set_defaults(func=cmd_watch)

    history = sub.add_parser("history", help="历史统计（已结束的战争）")
    history.add_argument("--limit", type=int, default=20)
    history.set_defaults(func=cmd_history)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
