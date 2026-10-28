#!/usr/bin/env python3
"""
OpenRota — kişisel yapay zeka ile öğrenme.
Anched AI motoru arka planda hızlı uyum sağlar.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openrota.assistant import LearningAssistant  # noqa: E402  # paket: openrota/openrota/


def main() -> None:
    assistant = LearningAssistant()

    def print_msg(text: str) -> None:
        print("\n[Asistan]", text, flush=True)

    assistant.set_message_handler(print_msg)
    print("OpenRota başladı. Çıkmak için 'q' yazın.\n")
    assistant.start_background()
    assistant.emit_startup_sync()
    if assistant.profile:
        print("(Kayıtlı profil yüklendi.)\n")

    while True:
        try:
            line = input("Sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        if assistant.profile is None:
            assistant.apply_onboarding_reply(line)
        else:
            # Basit etkileşim: motoru besle
            assistant.engine.fast_train([(line, 0.5)], steps=1)
            print_msg(assistant.engine.infer(line, " ".join(assistant.profile.interests)))

    assistant.stop()
    print("Görüşmek üzere.")


if __name__ == "__main__":
    main()
