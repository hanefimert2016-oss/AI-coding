"""Kişiselleştirilmiş ders rotası üretimi."""

from __future__ import annotations

from dataclasses import dataclass

from .store import UserProfile


@dataclass
class Lesson:
    id: str
    title: str
    minutes: int
    video_url: str
    summary: str


# Örnek konu havuzu — ilgi alanlarına göre seçilir
_TOPIC_POOL: dict[str, list[tuple[str, str]]] = {
    "yapay_zeka": [
        ("Giriş: ML nedir?", "https://www.youtube.com/watch?v=aircAruvnKk"),
        ("Sinir ağları özeti", "https://www.youtube.com/watch?v=IHZwWFHWa-w"),
        ("Etik ve veri", "https://www.youtube.com/watch?v=Ht3sE-JoyaY"),
    ],
    "programlama": [
        ("Temel veri yapıları", "https://www.youtube.com/watch?v=RBSGKlAvoiM"),
        ("Algoritma düşüncesi", "https://www.youtube.com/watch?v=8hly31xKli0"),
    ],
    "matematik": [
        ("Türev sezgisi", "https://www.youtube.com/watch?v=9vK6dfr39os"),
        ("Lineer cebir özeti", "https://www.youtube.com/watch?v=fNk_zzaMoSs"),
    ],
    "genel": [
        ("Odaklanma teknikleri", "https://www.youtube.com/watch?v=H62hZBMUDBo"),
        ("Öğrenme nasıl kalıcı olur?", "https://www.youtube.com/watch?v=IlU-zDU6aQ0"),
    ],
}


def _topics_for_profile(p: UserProfile) -> list[str]:
    keys: list[str] = []
    text = " ".join(p.interests + p.topics_liked).lower()
    if any(x in text for x in ("yapay", "ai", "zeka", "ml", "makine")):
        keys.append("yapay_zeka")
    if any(x in text for x in ("kod", "yazılım", "python", "program")):
        keys.append("programlama")
    if any(x in text for x in ("matematik", "istatistik", "sayı")):
        keys.append("matematik")
    if not keys:
        keys = ["genel"]
    return keys


def build_route(profile: UserProfile) -> list[Lesson]:
    """Profil ve yıllık süreye göre kısa derslerden rota."""
    topics = _topics_for_profile(profile)
    lessons: list[Lesson] = []
    idx = 0
    for tk in topics:
        for title, url in _TOPIC_POOL.get(tk, _TOPIC_POOL["genel"]):
            lid = f"L{idx+1:03d}"
            minutes = 8 if profile.pace == "yavaş" else 5 if profile.pace == "normal" else 4
            lessons.append(
                Lesson(
                    id=lid,
                    title=title,
                    minutes=minutes,
                    video_url=url,
                    summary=f"{title} — kısa video + not.",
                )
            )
            idx += 1
    # Yıllık süreye göre ders sayısını sınırla (kabaca)
    max_lessons = max(3, min(24, profile.year_hours // 8))
    return lessons[:max_lessons]
