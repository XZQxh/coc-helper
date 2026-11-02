from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coc_helper.api import WarResult
from coc_helper.store import Store

WAR = {
    "state": "warEnded",
    "teamSize": 2,
    "attacksPerMember": 1,
    "startTime": "20261101T000000.000Z",
    "endTime": "20261102T000000.000Z",
    "clan": {
        "tag": "#TEST",
        "name": "Test",
        "stars": 5,
        "destructionPercentage": 90.0,
        "members": [
            {
                "tag": "#A",
                "name": "Alice",
                "townhallLevel": 15,
                "mapPosition": 1,
                "attacks": [{"stars": 3, "destructionPercentage": 100}],
            },
            {
                "tag": "#B",
                "name": "Bob",
                "townhallLevel": 14,
                "mapPosition": 2,
                "attacks": [{"stars": 2, "destructionPercentage": 80}],
            },
        ],
    },
    "opponent": {
        "tag": "#OPP",
        "name": "Opp",
        "stars": 4,
        "destructionPercentage": 80.0,
        "members": [],
    },
}


class StoreTest(unittest.TestCase):
    def test_member_history_and_recent_wars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "test.db")
            try:
                result = WarResult(
                    war=WAR, kind="regular", war_tag=None, our_side="clan"
                )
                store.upsert_war("#TEST", result)

                rows = {
                    row["player_tag"]: row
                    for row in store.member_history("#TEST", 10)
                }
                self.assertIn("#A", rows)
                self.assertEqual(rows["#A"]["attacks_used"], 1)
                self.assertEqual(rows["#A"]["attacks_allowed"], 1)
                self.assertEqual(rows["#A"]["three_star"], 1)
                self.assertEqual(rows["#A"]["wars"], 1)

                recent = store.recent_wars("#TEST", 10)
                self.assertEqual(len(recent), 1)
                self.assertEqual(recent[0]["opponent_name"], "Opp")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
