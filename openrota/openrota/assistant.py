"""Arka planda çalışan küçük yapay zeka asistanı — sorular ve kısa dersler."""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import sys
from pathlib import Path

# Proje kökü (openrota/) — anched_ai için path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from anched_ai import get_engine  # noqa: E402

from .routes import Lesson, build_route
from .store import ProfileStore, UserProfile, random_year_hours


class LearningAssistant:
    """
    Arka plan iş parçacığında mesaj kuyruğu ile çalışır;
    ilk oturumda ilgi alanlarını sorar, rotayı kişiselleştirir.
    """

    def __init__(self, store: ProfileStore | None = None) -> None:
        self.store = store or ProfileStore()
        self.engine = get_engine()
        self._q: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._on_message: Callable[[str], None] | None = None
        self.profile: UserProfile | None = self.store.load()

    def set_message_handler(self, fn: Callable[[str], None]) -> None:
        self._on_message = fn

    def _emit(self, text: str) -> None:
        if self._on_message:
            self._on_message(text)
        self._q.put(text)

    def start_background(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def emit_startup_sync(self) -> None:
        """Karşılama ve ilk sorular — ana iş parçacığında (input ile çakışmasın)."""
        self._emit("OpenRota asistanı hazır. Anched AI motoru bağlandı.")
        if not self.profile:
            self._onboarding()
        else:
            self._daily_brief()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        """Sadece periyodik hatırlatma; karşılama emit_startup_sync ile yapılır."""
        while not self._stop.is_set():
            time.sleep(30)
            if self.profile:
                self._maybe_nudge()

    def _onboarding(self) -> None:
        self._emit(
            "Merhaba! Kişisel rotanı oluşturmak için birkaç soru:\n"
            "1) En çok hangi konulara ilgi duyuyorsun? (virgülle yaz)\n"
            "2) Öğrenme tempon: yavaş / normal / hızlı — hangisi?\n"
            "3) Günde yaklaşık kaç dakika ayırabilirsin? (sayı)\n\n"
            "Yanıtını tek mesajda yazabilirsin; örnek: yapay zeka, python | normal | 30"
        )

    def apply_onboarding_reply(self, text: str) -> None:
        """Kullanıcı yanıtını ayrıştır ve profili kaydet."""
        interests: list[str] = []
        pace = "normal"
        daily = 25

        if "|" in text:
            segs = [s.strip() for s in text.split("|")]
            raw_int = segs[0].replace(",", " ").replace(";", " ")
            interests = [x.strip() for x in raw_int.split() if x.strip()]
            if len(segs) > 1:
                low = segs[1].lower()
                if "yavaş" in low or "yavas" in low:
                    pace = "yavaş"
                elif "hız" in low or "hiz" in low:
                    pace = "hızlı"
                else:
                    pace = "normal"
            if len(segs) > 2:
                for tok in segs[2].split():
                    if tok.isdigit():
                        daily = int(tok)
                        break
        else:
            parts = [p.strip() for p in text.split(",")]
            for part in parts:
                low = part.lower()
                if any(x in low for x in ("yavaş", "yavas", "normal", "hızlı", "hızli")):
                    if "yavaş" in low or "yavas" in low:
                        pace = "yavaş"
                    elif "hız" in low or "hiz" in low:
                        pace = "hızlı"
                elif part.isdigit():
                    daily = int(part)
                else:
                    interests.extend([x.strip() for x in part.split() if x.strip()])

        if not interests:
            interests = ["genel öğrenme"]

        uid_seed = text[:64]
        yh = random_year_hours(uid_seed)
        p = self.store.new_user("")
        p.interests = interests[:20]
        p.topics_liked = interests[:]
        p.pace = pace
        p.daily_minutes = max(10, min(180, daily))
        p.year_hours = yh
        self.store.save(p)
        self.profile = p

        self.engine.fast_train([(t, 1.0) for t in interests], steps=2)
        self._emit(
            f"Profil kaydedildi. Bu yıl için hedefin yaklaşık {yh} saat çalışma; "
            f"günde ~{p.daily_minutes} dk. Rota aşağıda."
        )
        self._emit_route()

    def _daily_brief(self) -> None:
        assert self.profile is not None
        self._emit(f"Tekrar hoş geldin! Bugünkü hedef: kısa bir ders tamamla ({self.profile.daily_minutes} dk içinde).")
        self._emit_route()

    def _emit_route(self) -> None:
        if not self.profile:
            return
        lessons = build_route(self.profile)
        for les in lessons[:5]:
            self._emit(self._lesson_line(les))
        hint = self.engine.infer("sonraki adım", " ".join(self.profile.interests))
        self._emit(hint)

    def _lesson_line(self, les: Lesson) -> str:
        return (
            f"[Ders {les.id}] {les.title} ({les.minutes} dk) — Video: {les.video_url}\n"
            f"  Özet: {les.summary}"
        )

    def _maybe_nudge(self) -> None:
        self._emit("Küçük hatırlatma: bir sonraki kısa videoyu açıp not almayı dene.")

    def get_message(self, timeout: float | None = None) -> str | None:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None
