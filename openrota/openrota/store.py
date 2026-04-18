"""Kullanıcı profili ve rota kalıcılığı (JSON)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class UserProfile:
    user_id: str
    name: str = ""
    interests: list[str] = field(default_factory=list)
    pace: str = "normal"  # yavaş | normal | hızlı
    daily_minutes: int = 25
    year_hours: int = 120  # yıllık toplam çalışma süresi (saat) — herkes için farklı
    topics_liked: list[str] = field(default_factory=list)
    completed_lesson_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UserProfile:
        return cls(
            user_id=d["user_id"],
            name=d.get("name", ""),
            interests=list(d.get("interests", [])),
            pace=d.get("pace", "normal"),
            daily_minutes=int(d.get("daily_minutes", 25)),
            year_hours=int(d.get("year_hours", 120)),
            topics_liked=list(d.get("topics_liked", [])),
            completed_lesson_ids=list(d.get("completed_lesson_ids", [])),
        )


def _default_data_dir() -> Path:
    return Path(os.environ.get("OPENROTA_DATA", Path(__file__).resolve().parent / "data"))


class ProfileStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or _default_data_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._path = self._dir / "profile.json"

    def load(self) -> UserProfile | None:
        with self._lock:
            if not self._path.exists():
                return None
            with open(self._path, encoding="utf-8") as f:
                return UserProfile.from_dict(json.load(f))

    def save(self, profile: UserProfile) -> None:
        with self._lock:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

    def new_user(self, name: str = "") -> UserProfile:
        uid = str(uuid.uuid4())[:8]
        p = UserProfile(user_id=uid, name=name)
        self.save(p)
        return p


def random_year_hours(seed: str) -> int:
    """Her kullanıcı için farklı yıllık çalışma süresi (80–200 saat arası)."""
    h = sum(ord(c) for c in seed) % 121
    return 80 + h
