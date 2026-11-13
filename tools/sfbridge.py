"""Most Python <-> SoulsFormats (.NET) przez pythonnet.

Biblioteka: zbudowany SoulsFormats (net10) + zaleznosci + oo2core_6_win64.dll
(Oodle, potrzebny do DCX_KRAK z Elden Ring) w jednym katalogu.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_SF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work", "scratch", "sf", "pub"
)

_DEPS = (
    "BouncyCastle.Cryptography.dll", "DotNext.dll", "DotNext.IO.dll", "DotNext.Unsafe.dll",
    "Microsoft.Toolkit.HighPerformance.dll", "ZstdNet.dll",
)
_loaded = False


def load_soulsformats(sf_dir: str | None = None) -> Any:
    """Zaladuj SoulsFormats (idempotentnie) i zwroc modul `SoulsFormats`."""
    global _loaded
    if not _loaded:
        sf_dir = os.path.abspath(sf_dir or DEFAULT_SF_DIR)
        dll = os.path.join(sf_dir, "SoulsFormats.dll")
        if not os.path.exists(dll):
            raise FileNotFoundError(f"Brak SoulsFormats.dll w {sf_dir!r} (zob. --sf-dir).")
        if not os.path.exists(os.path.join(sf_dir, "oo2core_6_win64.dll")):
            raise FileNotFoundError(
                f"Brak oo2core_6_win64.dll w {sf_dir!r} - skopiuj go z katalogu ELDEN RING\\Game.")

        from pythonnet import load
        load("coreclr")
        import clr
        from System import Environment
        from System.Reflection import Assembly

        # SoulsFormats szuka oo2core w katalogu roboczym procesu.
        Environment.CurrentDirectory = sf_dir
        for dep in _DEPS:
            p = os.path.join(sf_dir, dep)
            if os.path.exists(p):
                Assembly.LoadFrom(p)
        clr.AddReference(dll)
        _loaded = True

    import SoulsFormats
    return SoulsFormats


def read_binder(cls: Any, path: str) -> Any:
    """BND3/BND4 z pliku (DCX rozpakowywany automatycznie)."""
    import SoulsFormats
    return SoulsFormats.MountedSoulsFile[cls].Read(path)


def read_file(cls: Any, source: Any) -> Any:
    """TAE/ESD z pliku (str) lub z `Memory<byte>` wpisu kontenera."""
    import SoulsFormats
    return SoulsFormats.SoulsFile[cls].Read(source)


def to_memory(net_bytes: Any) -> Any:
    """.NET `byte[]` -> `Memory<byte>` (do `BinderFile.Bytes`)."""
    from System import Byte, Memory
    return Memory[Byte](net_bytes)


def net_bytes(data: bytes) -> Any:
    """Python `bytes` -> .NET `byte[]`."""
    from System import Array, Byte
    return Array[Byte](list(data))
