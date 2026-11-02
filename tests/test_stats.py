from __future__ import annotations

import unittest

from coc_helper.stats import member_stats, team_totals

WAR = {
    "state": "inWar",
    "attacksPerMember": 2,
    "clan": {
        "members": [
            {
                "tag": "#ALICE",
                "name": "Alice",
                "townhallLevel": 15,
                "mapPosition": 1,
                "attacks": [
                    {"stars": 3, "destructionPercentage": 100},
                    {"stars": 2, "destructionPercentage": 80},
                ],
            },
            {
                "tag": "#BOB",
                "name": "Bob",
                "townhallLevel": 14,
                "mapPosition": 2,
            },
        ]
    },
    "opponent": {"members": []},
}


class StatsTest(unittest.TestCase):
    def test_member_rates(self) -> None:
        rows = {r.tag: r for r in member_stats(WAR, "clan")}
        alice = rows["#ALICE"]
        self.assertEqual(alice.attacks_used, 2)
        self.assertEqual(alice.attacks_allowed, 2)
        self.assertEqual(alice.stars, 5)
        self.assertAlmostEqual(alice.destruction, 180.0)
        self.assertEqual(alice.three_star, 1)
        self.assertAlmostEqual(alice.three_star_rate or 0, 0.5)
        self.assertAlmostEqual(alice.avg_destruction or 0, 90.0)

    def test_member_without_attacks(self) -> None:
        rows = {r.tag: r for r in member_stats(WAR, "clan")}
        bob = rows["#BOB"]
        self.assertEqual(bob.attacks_used, 0)
        self.assertIsNone(bob.three_star_rate)
        self.assertIsNone(bob.avg_destruction)

    def test_team_totals(self) -> None:
        totals = team_totals(WAR, "clan")
        self.assertEqual(totals["members"], 2)
        self.assertEqual(totals["attacks_used"], 2)
        self.assertEqual(totals["attacks_allowed"], 4)
        self.assertEqual(totals["stars"], 5)
        self.assertAlmostEqual(totals["three_star_rate"] or 0, 0.5)
        self.assertAlmostEqual(totals["avg_destruction"] or 0, 90.0)

    def test_empty_team(self) -> None:
        totals = team_totals(WAR, "opponent")
        self.assertEqual(totals["members"], 0)
        self.assertIsNone(totals["three_star_rate"])
        self.assertIsNone(totals["avg_destruction"])


if __name__ == "__main__":
    unittest.main()
