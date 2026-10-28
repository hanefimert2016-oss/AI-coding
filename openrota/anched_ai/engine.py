"""
Anched AI motoru: ağırlıkları ve önbelleği agresif güncelleyerek
normalden hızlı tepki ve kısa eğitim döngüleri sağlar.
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FastWeights:
    """Basit vektör temsili — hızlı güncelleme için yoğun bellek içi işlemler."""

    dim: int = 64
    w: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.w:
            h = hashlib.sha256(b"anched_ai_seed").digest()
            self.w = [((h[i % len(h)] / 255.0) - 0.5) * 0.2 for i in range(self.dim)]

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        out = list(self.w)
        for i, b in enumerate(h):
            out[i % self.dim] += (b / 255.0 - 0.5) * 0.05
        return out

    def train_step(self, text: str, label: float, lr: float = 0.35) -> float:
        """Tek adımda hızlı uyum — 'hızlı eğitim' simülasyonu."""
        e = self.embed(text)
        pred = math.tanh(sum(e) / len(e))
        err = label - pred
        for i in range(self.dim):
            self.w[i] += lr * err * e[i] * (1 - pred * pred + 1e-6)
        return abs(err)


class AnchedEngine:
    """
    Anched AI: arka planda hafif eğitim, ön yüzde milisaniye seviyesinde çıkarım.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._weights = _FastWeights()
        self._cache: dict[str, str] = {}
        self._train_ticks = 0
        self._last_train = 0.0

    def infer(self, prompt: str, context: str = "") -> str:
        """Hızlı çıkarım: önbellek + vektör tabanlı kısa yanıt."""
        key = hashlib.sha256(f"{prompt}|{context}".encode()).hexdigest()[:32]
        with self._lock:
            if key in self._cache:
                return self._cache[key]
            emb = self._weights.embed(prompt + context)
            score = sum(emb) / max(len(emb), 1)
            if score > 0.15:
                tone = "odaklı ve kısa"
            elif score < -0.1:
                tone = "örnekli"
            else:
                tone = "dengeli"
            out = (
                f"[Anched AI • {tone}] "
                f"İstek özeti işlendi. Öncelik: {abs(score):.2f}. "
                f"Öneri: bir sonraki adımı tek parça halinde uygula."
            )
            self._cache[key] = out
            if len(self._cache) > 500:
                drop = next(iter(self._cache))
                del self._cache[drop]
            return out

    def fast_train(self, samples: list[tuple[str, float]], steps: int = 3) -> dict[str, Any]:
        """Kullanıcı etkileşimlerinden hızlı uyum (birkaç mikro epoch)."""
        loss = 0.0
        with self._lock:
            for _ in range(steps):
                for text, label in samples:
                    loss += self._weights.train_step(text, label)
            self._train_ticks += len(samples) * steps
            self._last_train = time.time()
        return {"loss": round(loss / max(len(samples) * steps, 1), 4), "ticks": self._train_ticks}

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "engine": "Anched AI",
                "train_ticks": self._train_ticks,
                "last_train_ts": self._last_train,
                "cache_size": len(self._cache),
            }


_engine: AnchedEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> AnchedEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AnchedEngine()
        return _engine
