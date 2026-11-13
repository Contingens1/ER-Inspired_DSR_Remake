"""Dostep do soulstruct-havok (toolsy/soulstruct-havok, klon z GitHuba - nie instalowany przez pip).
Dokleja jego katalog src do przestrzeni nazw `soulstruct`, zeby dzialalo `import soulstruct.havok`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HAVOK_SRC = Path(__file__).resolve().parent.parent.parent / "toolsy" / "soulstruct-havok" / "src"


def load_havok():
    import soulstruct
    extra = str(HAVOK_SRC / "soulstruct")
    if extra not in list(soulstruct.__path__):
        soulstruct.__path__.append(extra)
    if str(HAVOK_SRC) not in sys.path:
        sys.path.append(str(HAVOK_SRC))
    import soulstruct.havok  # noqa: F401
    return soulstruct.havok
