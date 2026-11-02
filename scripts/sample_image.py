"""Generate sample war cards for visual inspection."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coc_helper.api import CocClient, WarResult  # noqa: E402
from coc_helper.config import load_settings  # noqa: E402
from coc_helper.render_image import render_history_image, render_war_image  # noqa: E402


def fake_war() -> WarResult:
    names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]
    results = [(3, 100), (2, 85), (3, 100), (1, 60), (2, 75), (3, 100), (0, 0), (2, 90)]
    members = []
    for i, (name, (stars, dest)) in enumerate(zip(names, results), 1):
        attacks = [{"stars": stars, "destructionPercentage": dest}] if stars else []
        members.append(
            {
                "tag": f"#SAMPLE{i}",
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
        war=war, kind="cwl", war_tag="#SAMPLE", our_side="clan", round_number=1
    )


def main() -> int:
    out_dir = ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    client = CocClient(settings.token)
    result = client.find_current_war(settings.clan_tag)
    if result:
        path = out_dir / "sample_real.png"
        path.write_bytes(render_war_image(result))
        print(f"{path} {path.stat().st_size} bytes")
    else:
        print("no current war for real sample")

    path = out_dir / "sample_fake.png"
    path.write_bytes(render_war_image(fake_war()))
    print(f"{path} {path.stat().st_size} bytes")

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
    path = out_dir / "sample_history.png"
    path.write_bytes(render_history_image("示例部落", history_rows, 20))
    print(f"{path} {path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
