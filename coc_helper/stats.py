"""War member statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemberStats:
    tag: str
    name: str
    townhall: int | None
    map_position: int | None
    attacks_used: int
    attacks_allowed: int
    stars: int
    destruction: float
    three_star: int

    @property
    def three_star_rate(self) -> float | None:
        return self.three_star / self.attacks_used if self.attacks_used else None

    @property
    def avg_destruction(self) -> float | None:
        return self.destruction / self.attacks_used if self.attacks_used else None


def member_stats(
    war: dict[str, Any], side: str = "clan", default_attacks: int = 2
) -> list[MemberStats]:
    team = war.get(side) or {}
    allowed = int(war.get("attacksPerMember") or default_attacks)
    rows: list[MemberStats] = []
    for member in team.get("members") or []:
        attacks = member.get("attacks") or []
        stars = sum(int(a.get("stars") or 0) for a in attacks)
        destruction = sum(float(a.get("destructionPercentage") or 0) for a in attacks)
        three = sum(1 for a in attacks if int(a.get("stars") or 0) == 3)
        rows.append(
            MemberStats(
                tag=str(member.get("tag") or ""),
                name=str(member.get("name") or ""),
                townhall=member.get("townhallLevel"),
                map_position=member.get("mapPosition"),
                attacks_used=len(attacks),
                attacks_allowed=allowed,
                stars=stars,
                destruction=destruction,
                three_star=three,
            )
        )
    return rows


def team_totals(
    war: dict[str, Any], side: str = "clan", default_attacks: int = 2
) -> dict[str, Any]:
    rows = member_stats(war, side, default_attacks)
    attacks_used = sum(r.attacks_used for r in rows)
    stars = sum(r.stars for r in rows)
    destruction = sum(r.destruction for r in rows)
    three = sum(r.three_star for r in rows)
    return {
        "members": len(rows),
        "attacks_used": attacks_used,
        "attacks_allowed": sum(r.attacks_allowed for r in rows),
        "stars": stars,
        "destruction": destruction,
        "three_star": three,
        "three_star_rate": three / attacks_used if attacks_used else None,
        "avg_destruction": destruction / attacks_used if attacks_used else None,
    }
