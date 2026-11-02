"""Verify Supercell API access for the configured clan.

Reads COC_API_TOKEN / COC_CLAN_TAG from .env, then checks:
  - clan info
  - current war (regular, or CWL via league group)
  - war log (public vs private)
  - current CWL league group
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def api(token: str, path: str) -> tuple[int | None, object]:
    url = "https://api.clashofclans.com/v1/" + path
    req = Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body
    except URLError as exc:
        return None, f"URLError: {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - surface any transport error
        return None, f"{type(exc).__name__}: {exc}"


def describe_war(data: dict) -> None:
    clan = data.get("clan") or {}
    opponent = data.get("opponent") or {}
    print(
        f"  state={data.get('state')} type={data.get('type')} "
        f"teamSize={data.get('teamSize')} attacksPerMember={data.get('attacksPerMember')}"
    )
    print(
        f"  our stars={clan.get('stars')} dest={clan.get('destructionPercentage')} "
        f"attacks={clan.get('attacks')} members={len(clan.get('members') or [])}"
    )
    print(
        f"  their stars={opponent.get('stars')} dest={opponent.get('destructionPercentage')} "
        f"attacks={opponent.get('attacks')} members={len(opponent.get('members') or [])}"
    )


def find_cwl_war(token: str, group: dict, clan_tag: str) -> tuple[str | None, dict | None]:
    """Return the war in the latest CWL round that includes clan_tag.

    League group rounds are lists of war tags; future rounds contain #0.
    """
    for round_data in reversed(group.get("rounds") or []):
        tags = [t for t in (round_data.get("warTags") or []) if t and t != "#0"]
        if not tags:
            continue
        for war_tag in tags:
            status, war = api(token, f"clanwarleagues/wars/{quote(war_tag, safe='')}")
            if status != 200 or not isinstance(war, dict):
                continue
            sides = {
                (war.get("clan") or {}).get("tag"),
                (war.get("opponent") or {}).get("tag"),
            }
            if clan_tag in sides:
                return war_tag, war
    return None, None


def main() -> int:
    env = load_env()
    token = env.get("COC_API_TOKEN", "")
    tag = env.get("COC_CLAN_TAG", "").strip()
    if not token or not tag:
        print("missing COC_API_TOKEN or COC_CLAN_TAG in .env")
        return 1

    tag = tag if tag.startswith("#") else "#" + tag
    encoded = quote(tag, safe="")
    print(f"token_length={len(token)} tag={tag}")

    clan_status, clan = api(token, f"clans/{encoded}")
    print(f"\n[clan] status={clan_status}")
    if isinstance(clan, dict) and clan_status == 200:
        print(
            f"  name={clan.get('name')} tag={clan.get('tag')} "
            f"level={clan.get('clanLevel')} members={len(clan.get('memberList') or [])}"
        )
    elif isinstance(clan, dict):
        print(f"  reason={clan.get('reason')} message={clan.get('message')}")

    cw_status, war = api(token, f"clans/{encoded}/currentwar")
    print(f"\n[currentwar] status={cw_status}")
    if isinstance(war, dict) and cw_status == 200:
        describe_war(war)
        if war.get("state") == "notInWar":
            lg_status, group = api(token, f"clans/{encoded}/currentwar/leaguegroup")
            print(f"\n[leaguegroup] status={lg_status}")
            if isinstance(group, dict) and lg_status == 200:
                print(
                    f"  state={group.get('state')} season={group.get('season')} "
                    f"rounds={len(group.get('rounds') or [])}"
                )
                war_tag, cwl_war = find_cwl_war(token, group, tag)
                if cwl_war:
                    print(f"\n[cwl-war] war_tag={war_tag}")
                    describe_war(cwl_war)
                else:
                    print("  no current CWL war found for this clan")
            elif isinstance(group, dict):
                print(f"  reason={group.get('reason')} message={group.get('message')}")

    wl_status, warlog = api(token, f"clans/{encoded}/warlog")
    print(f"\n[warlog] status={wl_status}")
    if isinstance(warlog, dict) and wl_status == 200:
        items = warlog.get("items") or []
        print(f"  items={len(items)}")
        if items:
            first = items[0]
            print(
                f"  first_end={first.get('endTime')} result={first.get('result')} "
                f"teamSize={first.get('teamSize')}"
            )
    elif isinstance(warlog, dict):
        print(f"  reason={warlog.get('reason')} message={warlog.get('message')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
