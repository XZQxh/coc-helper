"""Configuration loaded from .env."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    path = path or ROOT / ".env"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


@dataclass(frozen=True)
class Settings:
    token: str
    clan_tag: str
    db_path: Path
    poll_war: int = 60
    poll_prep: int = 300


def load_settings() -> Settings:
    env = load_dotenv()
    token = env.get("COC_API_TOKEN", "").strip()
    clan_tag = env.get("COC_CLAN_TAG", "").strip()
    if not token:
        raise SystemExit("缺少 COC_API_TOKEN，请先填 .env")
    if not clan_tag:
        raise SystemExit("缺少 COC_CLAN_TAG，请先填 .env")
    if not clan_tag.startswith("#"):
        clan_tag = "#" + clan_tag
    db_path = Path(env.get("DB_PATH", "data/coc.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    return Settings(
        token=token,
        clan_tag=clan_tag.upper(),
        db_path=db_path,
        poll_war=int(env.get("POLL_INTERVAL_WAR", "60") or 60),
        poll_prep=int(env.get("POLL_INTERVAL_PREP", "300") or 300),
    )
