from __future__ import annotations

import unittest

from coc_helper.api import WarResult
from coc_helper.render import format_attacks

WAR = {
    "state": "inWar",
    "teamSize": 1,
    "attacksPerMember": 1,
    "clan": {
        "name": "Us",
        "members": [
            {
                "tag": "#A",
                "name": "Alice",
                "townhallLevel": 15,
                "mapPosition": 1,
                "attacks": [
                    {
                        "order": 1,
                        "attackerTag": "#A",
                        "defenderTag": "#X",
                        "stars": 3,
                        "destructionPercentage": 100,
                    }
                ],
            }
        ],
    },
    "opponent": {
        "name": "Them",
        "members": [
            {
                "tag": "#X",
                "name": "Bob",
                "townhallLevel": 14,
                "mapPosition": 1,
                "attacks": [
                    {
                        "order": 1,
                        "attackerTag": "#X",
                        "defenderTag": "#A",
                        "stars": 2,
                        "destructionPercentage": 80,
                    }
                ],
            }
        ],
    },
}


class RenderTest(unittest.TestCase):
    def test_format_attacks(self) -> None:
        result = WarResult(
            war=WAR, kind="regular", war_tag=None, our_side="clan", round_number=1
        )
        text = format_attacks(result)
        self.assertIn("对手：Them", text)
        self.assertIn("我方进攻（1 次）", text)
        self.assertIn("对方进攻（1 次）", text)
        self.assertIn("Alice", text)
        self.assertIn("Bob", text)
        self.assertIn("3★ 100.0%", text)
        self.assertIn("2★ 80.0%", text)


if __name__ == "__main__":
    unittest.main()
