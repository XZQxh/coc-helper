"""Render a war summary as a PNG card."""

from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .api import WarResult
from .stats import member_stats, team_totals

WIDTH = 760
PAD = 28
BG = (243, 244, 246)
CARD = (255, 255, 255)
TEXT = (17, 24, 39)
MUTED = (107, 114, 128)
ACCENT = (217, 119, 6)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
LINE = (229, 231, 235)
ROW_ALT = (249, 250, 251)

FONT_REGULAR = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
FONT_BOLD = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


@lru_cache(maxsize=64)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    env = os.environ.get("COC_FONT_BOLD" if bold else "COC_FONT")
    candidates = ([env] if env else []) + (FONT_BOLD if bold else FONT_REGULAR)
    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise RuntimeError("找不到中文字体；设置 COC_FONT 指向 .ttf/.ttc")


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def _rate(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def _num(value: float | None) -> float:
    return float(value) if value is not None else 0.0


def _state_cn(state: str | None) -> str:
    return {
        "preparation": "准备期",
        "inWar": "进行中",
        "warEnded": "已结束",
        "notInWar": "未开战",
    }.get(state or "", state or "?")


def render_war_image(result: WarResult) -> bytes:
    war = result.war
    our = war.get(result.our_side) or {}
    their = war.get("opponent" if result.our_side == "clan" else "clan") or {}
    kind = "部落对战联赛" if result.kind == "cwl" else "部落战"
    round_text = f" · 第 {result.round_number} 场" if result.round_number else ""
    state = _state_cn(war.get("state"))
    team_size = war.get("teamSize") or "?"
    default_attacks = 1 if result.kind == "cwl" else 2
    totals = team_totals(war, result.our_side, default_attacks)
    rows = member_stats(war, result.our_side, default_attacks)

    header_h = 150
    table_h = 40
    row_h = 38
    height = header_h + table_h + row_h * len(rows) + 48
    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (10, 10, WIDTH - 10, height - 10), radius=18, fill=CARD, outline=LINE, width=1
    )

    name = str(our.get("name") or "未知部落")
    draw.text((PAD, 28), name, font=_font(26, True), fill=TEXT, anchor="lt")
    badge = f"{kind}{round_text} · {state} · {team_size}v{team_size}"
    draw.text((WIDTH - PAD, 30), badge, font=_font(14), fill=ACCENT, anchor="rt")
    draw.text(
        (PAD, 64),
        f"对手：{their.get('name') or '?'}",
        font=_font(13),
        fill=MUTED,
        anchor="lt",
    )

    draw.text(
        (PAD, 88),
        f"我方  {our.get('stars', 0)}★  {_num(our.get('destructionPercentage')):.1f}%",
        font=_font(22, True),
        fill=GREEN,
        anchor="lt",
    )
    draw.text(
        (WIDTH - PAD, 88),
        f"{their.get('stars', 0)}★  {_num(their.get('destructionPercentage')):.1f}%",
        font=_font(22, True),
        fill=RED,
        anchor="rt",
    )

    meta = (
        f"进攻 {totals['attacks_used']}/{totals['attacks_allowed']}   "
        f"三星率 {_rate(totals['three_star_rate'])}   "
        f"平均摧毁 {_pct(totals['avg_destruction'])}"
    )
    draw.text((PAD, 120), meta, font=_font(14), fill=MUTED, anchor="lt")
    if result.war_tag:
        draw.text((WIDTH - PAD, 120), result.war_tag, font=_font(13), fill=MUTED, anchor="rt")
    draw.line((PAD, 144, WIDTH - PAD, 144), fill=LINE, width=1)

    y = header_h
    cols = [
        ("#", 28, "lt"),
        ("成员", 64, "lt"),
        ("大本营", 420, "rt"),
        ("进攻", 490, "rt"),
        ("星", 545, "rt"),
        ("摧毁", 615, "rt"),
        ("三星率", 732, "rt"),
    ]
    for label, x, anchor in cols:
        draw.text((x, y), label, font=_font(13), fill=MUTED, anchor=anchor)

    y = header_h + 28
    for i, row in enumerate(rows, 1):
        if i % 2 == 0:
            draw.rectangle((22, y - 16, WIDTH - 22, y + 16), fill=ROW_ALT)
        draw.text((28, y), str(i), font=_font(13), fill=MUTED, anchor="lm")
        draw.text((64, y), row.name[:14], font=_font(15), fill=TEXT, anchor="lm")
        draw.text((420, y), str(row.townhall or "-"), font=_font(13), fill=TEXT, anchor="rm")
        draw.text(
            (490, y),
            f"{row.attacks_used}/{row.attacks_allowed}",
            font=_font(13),
            fill=TEXT,
            anchor="rm",
        )
        draw.text((545, y), str(row.stars), font=_font(13), fill=TEXT, anchor="rm")
        draw.text((615, y), _pct(row.avg_destruction), font=_font(13), fill=TEXT, anchor="rm")
        rate_color = ACCENT if row.attacks_used else MUTED
        draw.text(
            (732, y),
            _rate(row.three_star_rate),
            font=_font(13),
            fill=rate_color,
            anchor="rm",
        )
        y += row_h

    draw.text(
        (PAD, height - 30),
        "Supercell API · 数据可能有缓存延迟",
        font=_font(11),
        fill=MUTED,
        anchor="lt",
    )

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def render_history_image(
    clan_name: str, rows: list[dict], limit: int = 20
) -> bytes:
    rows = sorted(
        rows,
        key=lambda row: (
            float(row.get("three_star") or 0) / int(row.get("attacks_used") or 1)
            if int(row.get("attacks_used") or 0)
            else -1.0
        ),
        reverse=True,
    )
    header_h = 118
    row_h = 36
    height = header_h + row_h * len(rows) + 58 if rows else 250
    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (10, 10, WIDTH - 10, height - 10), radius=18, fill=CARD, outline=LINE, width=1
    )

    draw.text((PAD, 28), clan_name, font=_font(26, True), fill=TEXT, anchor="lt")
    draw.text(
        (WIDTH - PAD, 30),
        f"历史统计 · 最近 {limit} 场",
        font=_font(15),
        fill=ACCENT,
        anchor="rt",
    )
    draw.text(
        (PAD, 70),
        "只统计已结束的战争 · 成员级数据从接入后开始积累",
        font=_font(13),
        fill=MUTED,
        anchor="lt",
    )

    if not rows:
        draw.text((PAD, 130), "还没有已结束的战争", font=_font(20, True), fill=TEXT, anchor="lt")
        draw.text(
            (PAD, 170),
            "等这场 CWL 打完，bot 存下来后就能看报表。",
            font=_font(14),
            fill=MUTED,
            anchor="lt",
        )
    else:
        y = header_h
        cols = [
            ("#", 28, "lt"),
            ("成员", 64, "lt"),
            ("场次", 420, "rt"),
            ("进攻", 480, "rt"),
            ("三星率", 560, "rt"),
            ("平均摧毁", 640, "rt"),
            ("参战率", 732, "rt"),
        ]
        for label, x, anchor in cols:
            draw.text((x, y), label, font=_font(13), fill=MUTED, anchor=anchor)

        y = header_h + 26
        for i, row in enumerate(rows, 1):
            if i % 2 == 0:
                draw.rectangle((22, y - 15, WIDTH - 22, y + 15), fill=ROW_ALT)
            attacks = int(row.get("attacks_used") or 0)
            allowed = int(row.get("attacks_allowed") or 0)
            three = int(row.get("three_star") or 0)
            destruction = float(row.get("destruction") or 0)
            rate = three / attacks if attacks else None
            avg_dest = destruction / attacks if attacks else None
            participation = attacks / allowed if allowed else None

            draw.text((28, y), str(i), font=_font(13), fill=MUTED, anchor="lm")
            draw.text(
                (64, y),
                str(row.get("name") or "")[:14],
                font=_font(15),
                fill=TEXT,
                anchor="lm",
            )
            draw.text(
                (420, y),
                str(row.get("wars") or 0),
                font=_font(13),
                fill=TEXT,
                anchor="rm",
            )
            draw.text(
                (480, y),
                f"{attacks}/{allowed}",
                font=_font(13),
                fill=TEXT,
                anchor="rm",
            )
            draw.text(
                (560, y),
                _rate(rate),
                font=_font(13),
                fill=ACCENT if attacks else MUTED,
                anchor="rm",
            )
            draw.text(
                (640, y),
                _pct(avg_dest),
                font=_font(13),
                fill=TEXT,
                anchor="rm",
            )
            draw.text(
                (732, y),
                _rate(participation),
                font=_font(13),
                fill=TEXT,
                anchor="rm",
            )
            y += row_h

    draw.text(
        (PAD, height - 30),
        f"样本：{len(rows)} 名成员 · 数据来自 Supercell API",
        font=_font(11),
        fill=MUTED,
        anchor="lt",
    )
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
