"""Generate generic screenshots for the README (no private data)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coc_helper.api import WarResult  # noqa: E402
from coc_helper.render_image import (  # noqa: E402
    render_history_image,
    render_war_image,
)


def demo_war() -> WarResult:
    names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]
    results = [(3, 100), (2, 88), (3, 100), (1, 62), (2, 76), (3, 100), (0, 0), (2, 91)]
    members = []
    for i, (name, (stars, dest)) in enumerate(zip(names, results), 1):
        attacks = [{"stars": stars, "destructionPercentage": dest}] if stars else []
        members.append(
            {
                "tag": f"#DEMO{i}",
                "name": name,
                "townhallLevel": 17 - (i % 3),
                "mapPosition": i,
                "attacks": attacks,
            }
        )
    war = {
        "state": "inWar",
        "type": "cwl",
        "teamSize": len(names),
        "attacksPerMember": 1,
        "clan": {
            "name": "示例部落",
            "stars": 16,
            "destructionPercentage": 87.5,
            "members": members,
        },
        "opponent": {
            "name": "对手部落",
            "stars": 12,
            "destructionPercentage": 80.0,
            "members": [],
        },
    }
    return WarResult(
        war=war, kind="cwl", war_tag="#DEMO", our_side="clan", round_number=3
    )


def main() -> int:
    out = ROOT / "docs" / "assets"
    out.mkdir(parents=True, exist_ok=True)

    war_path = out / "war-card.png"
    war_path.write_bytes(render_war_image(demo_war()))
    print(f"{war_path} {war_path.stat().st_size} bytes")

    history_rows = [
        {"name": "Alpha", "wars": 12, "attacks_used": 12, "attacks_allowed": 12, "stars": 30, "destruction": 1120.0, "three_star": 6},
        {"name": "Bravo", "wars": 12, "attacks_used": 11, "attacks_allowed": 12, "stars": 26, "destruction": 1010.0, "three_star": 5},
        {"name": "Charlie", "wars": 10, "attacks_used": 10, "attacks_allowed": 10, "stars": 25, "destruction": 940.0, "three_star": 4},
        {"name": "Delta", "wars": 12, "attacks_used": 9, "attacks_allowed": 12, "stars": 18, "destruction": 760.0, "three_star": 2},
        {"name": "Echo", "wars": 8, "attacks_used": 8, "attacks_allowed": 8, "stars": 20, "destruction": 790.0, "three_star": 3},
        {"name": "Foxtrot", "wars": 12, "attacks_used": 10, "attacks_allowed": 12, "stars": 21, "destruction": 860.0, "three_star": 3},
        {"name": "Golf", "wars": 12, "attacks_used": 6, "attacks_allowed": 12, "stars": 10, "destruction": 420.0, "three_star": 1},
        {"name": "Hotel", "wars": 9, "attacks_used": 9, "attacks_allowed": 9, "stars": 19, "destruction": 770.0, "three_star": 2},
    ]
    history_path = out / "history-card.png"
    history_path.write_bytes(render_history_image("示例部落", history_rows, 20))
    print(f"{history_path} {history_path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
