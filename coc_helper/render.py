"""Format war data for the CLI and chat replies."""

from __future__ import annotations

from .api import WarResult
from .stats import member_stats, team_totals


def _pct(value: float | None) -> str:
    """Format a 0-100 percentage."""
    return "-" if value is None else f"{value:.1f}%"


def _rate(value: float | None) -> str:
    """Format a 0-1 ratio as a percentage."""
    return "-" if value is None else f"{value * 100:.1f}%"


def _num(value: float | None) -> float:
    return float(value) if value is not None else 0.0


def format_summary(result: WarResult) -> str:
    war = result.war
    our = war.get(result.our_side) or {}
    their = war.get("opponent" if result.our_side == "clan" else "clan") or {}
    kind = "部落对战联赛" if result.kind == "cwl" else "部落战"
    round_text = f" 第 {result.round_number} 场" if result.round_number else ""
    team_size = war.get("teamSize") or "?"
    lines = [
        f"{kind}{round_text} | {war.get('state') or '?'} | {team_size}v{team_size} | "
        f"我方 {our.get('stars', 0)}★ {_num(our.get('destructionPercentage')):.1f}% | "
        f"对方 {their.get('stars', 0)}★ {_num(their.get('destructionPercentage')):.1f}%"
    ]
    if their.get("name"):
        lines.append(f"对手: {their.get('name')}")
    if result.war_tag:
        lines.append(f"war_tag: {result.war_tag}")
    if war.get("startTime"):
        lines.append(f"start: {war['startTime']}  end: {war.get('endTime')}")

    default_attacks = 1 if result.kind == "cwl" else 2
    totals = team_totals(war, result.our_side, default_attacks)
    lines.append(
        f"进攻: {totals['attacks_used']}/{totals['attacks_allowed']} | "
        f"三星率: {_rate(totals['three_star_rate'])} | "
        f"平均摧毁: {_pct(totals['avg_destruction'])}"
    )
    return "\n".join(lines)


def format_members(result: WarResult) -> str:
    war = result.war
    default_attacks = 1 if result.kind == "cwl" else 2
    lines = [f"{'成员':<16}{'大本营':>6}{'进攻':>8}{'星':>4}{'摧毁':>9}{'三星率':>9}"]
    for row in member_stats(war, result.our_side, default_attacks):
        name = row.name[:12]
        th = row.townhall if row.townhall is not None else "-"
        attacks = f"{row.attacks_used}/{row.attacks_allowed}"
        lines.append(
            f"{name:<16}{th:>6}{attacks:>8}"
            f"{row.stars:>4}{_pct(row.avg_destruction):>9}{_rate(row.three_star_rate):>9}"
        )
    return "\n".join(lines)


def format_members_lines(result: WarResult) -> str:
    """One member per line, so QQ's proportional font cannot misalign columns."""
    war = result.war
    default_attacks = 1 if result.kind == "cwl" else 2
    lines: list[str] = []
    for index, row in enumerate(
        member_stats(war, result.our_side, default_attacks), 1
    ):
        th = f"大本营{row.townhall}" if row.townhall is not None else "大本营?"
        lines.append(
            f"{index}. {row.name} {th} "
            f"{row.attacks_used}/{row.attacks_allowed} {row.stars}★ "
            f"摧毁 {_pct(row.avg_destruction)} "
            f"三星率 {_rate(row.three_star_rate)}"
        )
    return "\n".join(lines)


def format_war(result: WarResult) -> str:
    return format_summary(result) + "\n\n" + format_members(result)


def _fmt_date(value: str | None) -> str:
    if not value:
        return "?"
    if len(value) >= 10 and value[4] == "-":
        return value[:10]
    if len(value) >= 8:
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
    return value


def format_history_lines(rows: list[dict]) -> str:
    if not rows:
        return "还没有已结束的战争。"
    lines: list[str] = []
    for index, row in enumerate(rows, 1):
        attacks = int(row.get("attacks_used") or 0)
        allowed = int(row.get("attacks_allowed") or 0)
        three = int(row.get("three_star") or 0)
        destruction = float(row.get("destruction") or 0)
        rate = three / attacks if attacks else None
        avg = destruction / attacks if attacks else None
        part = attacks / allowed if allowed else None
        lines.append(
            f"{index}. {row.get('name') or ''} {row.get('wars') or 0}场 "
            f"{attacks}/{allowed} 三星率 {_rate(rate)} "
            f"平均摧毁 {_pct(avg)} 参战率 {_rate(part)}"
        )
    return "\n".join(lines)


def format_recent_wars(rows: list[dict]) -> str:
    if not rows:
        return "还没有已结束的战争。"
    lines = [f"最近 {len(rows)} 场"]
    for index, row in enumerate(rows, 1):
        our = int(row.get("our_stars") or 0)
        their = int(row.get("their_stars") or 0)
        result = "胜" if our > their else "负" if our < their else "平"
        lines.append(
            f"{index}. {_fmt_date(row.get('end_time') or row.get('start_time'))} "
            f"vs {row.get('opponent_name') or '?'} {our}★/{their}★ {result}"
        )
    return "\n".join(lines)


def format_attacks(result: WarResult) -> str:
    war = result.war
    our = war.get(result.our_side) or {}
    their = war.get("opponent" if result.our_side == "clan" else "clan") or {}
    their_side = "opponent" if result.our_side == "clan" else "clan"
    default_attacks = 1 if result.kind == "cwl" else 2

    our_members = {m.get("tag"): m for m in (our.get("members") or [])}
    their_members = {m.get("tag"): m for m in (their.get("members") or [])}

    def name(member: dict | None) -> str:
        if not member:
            return "?"
        return str(member.get("name") or member.get("tag") or "?")

    def pos(member: dict | None) -> str:
        if not member:
            return "?"
        return str(member.get("mapPosition") or "?")

    def th(member: dict | None) -> str:
        if not member:
            return "?"
        return str(member.get("townhallLevel") or "?")

    def collect(attackers: dict, defenders: dict):
        rows = []
        for member in attackers.values():
            for attack in member.get("attacks") or []:
                rows.append(
                    (
                        int(attack.get("order") or 0),
                        member,
                        defenders.get(attack.get("defenderTag")),
                        attack,
                    )
                )
        rows.sort(key=lambda item: item[0])
        return rows

    our_attacks = collect(our_members, their_members)
    their_attacks = collect(their_members, our_members)

    defense: dict = {}
    for _, _, defender, attack in our_attacks:
        if not defender:
            continue
        tag = defender.get("tag")
        item = defense.setdefault(tag, {"count": 0, "stars": 0, "best": (0, 0.0)})
        stars = int(attack.get("stars") or 0)
        dest = float(attack.get("destructionPercentage") or 0)
        item["count"] += 1
        item["stars"] += stars
        if (stars, dest) > item["best"]:
            item["best"] = (stars, dest)

    lines = [f"对手：{their.get('name') or '?'}", "", "对方成员"]
    for index, row in enumerate(member_stats(war, their_side, default_attacks), 1):
        item = defense.get(row.tag, {"count": 0, "stars": 0, "best": (0, 0.0)})
        best_stars, best_dest = item["best"]
        best_text = f"{best_stars}★ {_pct(best_dest)}" if item["count"] else "-"
        lines.append(
            f"{index}. {row.name}（#{row.map_position or '?'}） 大本营{row.townhall or '?'} "
            f"进攻 {row.attacks_used}/{row.attacks_allowed} {row.stars}★ "
            f"被进攻 {item['count']} 次 被打 {item['stars']}★ 最高 {best_text}"
        )

    lines.append("")
    lines.append(f"我方进攻（{len(our_attacks)} 次）")
    if not our_attacks:
        lines.append("还没有进攻记录。")
    for index, (_, attacker, defender, attack) in enumerate(our_attacks, 1):
        lines.append(
            f"{index}. {name(attacker)}（#{pos(attacker)}） → "
            f"{name(defender)}（#{pos(defender)} / 大本营{th(defender)}） "
            f"{attack.get('stars') or 0}★ "
            f"{_pct(attack.get('destructionPercentage'))}"
        )

    lines.append("")
    lines.append(f"对方进攻（{len(their_attacks)} 次）")
    if not their_attacks:
        lines.append("还没有进攻记录。")
    for index, (_, attacker, defender, attack) in enumerate(their_attacks, 1):
        lines.append(
            f"{index}. {name(attacker)}（#{pos(attacker)} / 大本营{th(attacker)}） → "
            f"{name(defender)}（#{pos(defender)}） "
            f"{attack.get('stars') or 0}★ "
            f"{_pct(attack.get('destructionPercentage'))}"
        )

    return "\n".join(lines)
