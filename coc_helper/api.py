"""Minimal Supercell API client (stdlib only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "https://api.clashofclans.com/v1"


class CocApiError(Exception):
    def __init__(self, status: int | None, reason: str, message: str = ""):
        self.status = status
        self.reason = reason
        self.message = message
        super().__init__(f"HTTP {status}: {reason} {message}".strip())


def normalize_tag(tag: str) -> str:
    tag = tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag
    return tag


def encode_tag(tag: str) -> str:
    return quote(normalize_tag(tag), safe="")


@dataclass
class WarResult:
    war: dict[str, Any]
    kind: str  # "regular" | "cwl"
    war_tag: str | None
    our_side: str  # "clan" | "opponent"
    round_number: int | None = None
    league_group: dict[str, Any] | None = None


class CocClient:
    def __init__(self, token: str, timeout: float = 20.0):
        self.token = token
        self.timeout = timeout

    def _request(self, path: str) -> dict[str, Any]:
        url = f"{BASE_URL}/{path.lstrip('/')}"
        req = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            reason = ""
            message = ""
            try:
                payload = json.loads(body)
                reason = payload.get("reason", "")
                message = payload.get("message", "")
            except Exception:
                message = body[:300]
            raise CocApiError(exc.code, reason, message) from exc
        except URLError as exc:
            raise CocApiError(None, "network", str(exc.reason)) from exc

    def get_clan(self, tag: str) -> dict[str, Any]:
        return self._request(f"clans/{encode_tag(tag)}")

    def get_current_war(self, tag: str) -> dict[str, Any]:
        return self._request(f"clans/{encode_tag(tag)}/currentwar")

    def get_league_group(self, tag: str) -> dict[str, Any]:
        return self._request(f"clans/{encode_tag(tag)}/currentwar/leaguegroup")

    def get_cwl_war(self, war_tag: str) -> dict[str, Any]:
        return self._request(f"clanwarleagues/wars/{encode_tag(war_tag)}")

    def get_warlog(self, tag: str) -> dict[str, Any]:
        return self._request(f"clans/{encode_tag(tag)}/warlog")

    def find_current_war(self, clan_tag: str) -> WarResult | None:
        """Return the current regular war or CWL war for the clan."""
        clan_tag = normalize_tag(clan_tag)

        war = self.get_current_war(clan_tag)
        if war.get("state") not in (None, "notInWar"):
            return WarResult(
                war=war,
                kind="regular",
                war_tag=war.get("warTag"),
                our_side="clan",
            )

        try:
            group = self.get_league_group(clan_tag)
        except CocApiError as exc:
            if exc.status == 404:
                return None
            raise

        rounds = group.get("rounds") or []
        for round_index in range(len(rounds) - 1, -1, -1):
            round_data = rounds[round_index]
            for war_tag in round_data.get("warTags") or []:
                if not war_tag or war_tag == "#0":
                    continue
                try:
                    cwl_war = self.get_cwl_war(war_tag)
                except CocApiError as exc:
                    if exc.status in (403, 404):
                        continue
                    raise

                if clan_tag == (cwl_war.get("clan") or {}).get("tag"):
                    return WarResult(
                        war=cwl_war,
                        kind="cwl",
                        war_tag=war_tag,
                        our_side="clan",
                        round_number=round_index + 1,
                        league_group=group,
                    )
                if clan_tag == (cwl_war.get("opponent") or {}).get("tag"):
                    return WarResult(
                        war=cwl_war,
                        kind="cwl",
                        war_tag=war_tag,
                        our_side="opponent",
                        round_number=round_index + 1,
                        league_group=group,
                    )
        return None
