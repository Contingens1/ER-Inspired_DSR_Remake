"""
convert_er_c0000_to_dsr.py - Narzedzie portu silnika postaci z ER do DSR.

Cel:
  1) Rozpakowac z ER: c0000.behabnd.dcx (grafy zachowan / HKS) oraz
     c0000.anibnd.dcx (animacje / HKX) i zinwentaryzowac ich zawartosc.
  2) Porownac "naglowki klas Havoka" miedzy ER a DSR:
     - zestaw nazw klas (hkPhysics2010::..., hkAnimationContainer, ...)
     - znaczniki sekcji HKX (HKXD/HKXC/HKSS/HKSC/...)
     - wersje / buildy Havoka odczytane z samych plikow.
  3) Wyciagnac graf zachowan (Behavior State Machine) z HKS w ER i zmapowac
     stany podstawowe (Jump, Roll, ItemUse) na struktury akceptowalne przez
     silnik DSR (Havok 2010.1, 64-bit).

Zasady:
  - Skrypt NIGDY nie zapisuje niczego w katalogach gier. Wszystkie wyniki
    trafiaja do katalogu --out.
  - Wszystkie parsowanie jest "best effort": kazdy krok raportuje poziom
    pewnosci (heuristic / validated). Jesli format HKS/HKX nie zostal
    rozpoznany, skrypt mowi to wprost, zamiast zmyślac wynik.
  - Formaty HKS (skrypt behawioru) i HKX (animacja) nie maja publicznej
    specyfikacji; implementacja ponizej opiera sie na skanowaniu struktur
    (tagi sekcji, tabela stringow, bloki stanow) i na walidacji kazdego
    odczytu (offsety musza trafic w sensowne miejsce w pliku).

Uzycie (CMD):
    python tools\\convert_er_c0000_to_dsr.py ^
        --er-chr "C:\\Users\\nemos\\workspace\\nuxe\\chr" ^
        --dsr-chr "<sciezka do DSR>\\chr" ^
        --out work\\havok-port

Autor: rekonesans dla projektu "Souls Stance & Combat Overhaul" (ER -> DSR).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Import lokalnych narzedzi (dcx.py / bnd.py) z katalogu tools/
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import bnd as bndmod  # noqa: E402  (import po ustawieniu sys.path)

# ---------------------------------------------------------------------------
# Stale
# ---------------------------------------------------------------------------

ER_BEHAVIOR_NAMES = ("c0000.behabnd.dcx", "c0000.behbnd.dcx")
ER_ANIM_NAMES = ("c0000.anibnd.dcx",)

# Katalog z plikami ER wskazany przez uzytkownika (nadpisz --er-chr).
DEFAULT_ER_CHR = Path(r"C:\Users\nemos\workspace\nuxe\chr")

# Znaczniki sekcji Havoka, ktore sa istotne dla portu (animacja + behawior).
# Reszta sekcji jest wykrywana automatycznie przez skaner tagow.
KNOWN_HKX_TAGS = {
    "HKXD": "hkxData",
    "HKXC": "hkxCharacteristics",
    "HKSS": "hkxNodeSection (mesh/geometry)",
    "HKSC": "hkxSection (character/controller)",
    "HKBE": "hkxBehaviour",
    "HKSG": "hkxShapeGenerator (rig)",
    "HKMD": "hkxMesh",
    "HKTG": "hkxTexture",
    "HKCV": "hkxCollision",
    "HKHO": "hkxHavokObject",
    "HKSI": "hkxShape (intermediate)",
    "HKDS": "hkxDDS (textury)",
    "HKBT": "hkxBlend",
    "HCLA": "hkClassName (naglowek klasy)",
    "HXLV": "hxLevel",
    "HKLB": "hkxLibrary",
    "HKLM": "hkxLibraryEntry",
    "HKUC": "hkxUserData",
    "HKUR": "hkxUserDataRegistry",
    "HKTR": "hkxTrack",
    "HKBE": "hkxBehaviour",
    "HKDD": "hkxDelta",
    "HKSE": "hkxSegment",
    "HKAD": "hkxAnimation",
    "HKPB": "hkxPhysicsBody",
    "HKPA": "hkxPhysicsBodyAnimation",
    "HKCR": "hkxCharacterController",
    "HKCM": "hkxCharacterMotion",
    "HKDC": "hkxDriver",
    "HKDP": "hkxDriverParameters",
    "HKTB": "hkxTrackBone",
    "HKVC": "hkxVector",
    "HKVM": "hkxVector4",
    "HKWG": "hkxWindingGroup",
    "HKWR": "hkxWinding",
    "HKAS": "hkxAnimationStream",
    "HKAR": "hkxAnimationRuntime",
    "HKCC": "hkxCamera",
    "HKHA": "hkxHavokAnimation",
    "HKHY": "hkxHierarchy",
    "HKPF": "hkxPhysicsFixture",
    "HKPL": "hkxPhysicsLayout",
    "HKPO": "hkxPhysicsObject",
    "HKPP": "hkxPhysicsPrimitives",
    "HKQA": "hkxPhysicsQuery",
    "HKRA": "hkxRagdoll",
    "HKRL": "hkxRagdollLimits",
    "HKSA": "hkxSkeleton",
    "HKSB": "hkxSkeletonBone",
    "HKSK": "hkxSkeleton",
    "HKSP": "hkxSplit",
    "HKST": "hkxStringTable",
    "HKTH": "hkxThread",
    "HKTM": "hkxTrackMatrix",
    "HKWB": "hkxWavelet",
}

# Wzorce nazw klas Havoka (np. hkPhysics2010::hkCharacterController).
_CLASS_RE = re.compile(rb"hk[A-Z][A-Za-z0-9_]*(?:::[A-Za-z0-9_]+)*")

# Wzorce identyfikatorow, ktore w HKS odpowiadaja stanom zachowania gracza.
# Kolejnosc ma znaczenie: pierwsza trafiona regula wygrywa.
ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ItemUse", re.compile(r"(item_?use|use_?item|useitem|drink|eat_?item|use_?pouch|quaff|item)", re.I)),
    ("Roll", re.compile(r"(roll|dodge|evade|step_?back|backstep|fall)", re.I)),
    ("Jump", re.compile(r"(jump|leap|hop)", re.I)),
    ("Step", re.compile(r"(step|stride|slide|turn|strafe|walk|run|sprint|dash)", re.I)),
    ("Guard", re.compile(r"(guard|block|parry|shield)", re.I)),
    ("Attack", re.compile(r"(attack|atk|slash|thrust|weapon|combo|swing)", re.I)),
    ("Magic", re.compile(r"(magic|sorcery|incant|pyramid|faith|miracle|buff)", re.I)),
    ("Aim", re.compile(r"(aim|bow|bow_|shoot|arrow|target|lock_?on|lockon)", re.I)),
    ("Sheathe", re.compile(r"(sheath|holster|unsheathe|draw)", re.I)),
    ("Death", re.compile(r"(death|die|dead|ko|critical)", re.I)),
    ("Damage", re.compile(r"(damage|hit|flinch|stagger|poise|damage_?reaction)", re.I)),
    ("Idle", re.compile(r"(idle|stand|wait|breathe|rest)", re.I)),
]

# Docelowe sloty stanow w DSR. Kazdy stan ER mapujemy na jeden z tych
# "roli" - docelowa implementacja DSR (Havok 2010.1, x64) wymaga, zeby
# stany o roznym charakterze (animacja vs. przejscie vs. parametr)
# mialy rozne pola.
DSR_STATE_SLOTS: dict[str, dict[str, Any]] = {
    "Jump": {
        "slot": "jump",
        "anim_group": "a00",
        "required_fields": ["anim_id", "height", "duration", "forward_shift"],
        "notes": "DSR: skok ma dedykowany set animacji + parametry w HKS wariantu gracza.",
    },
    "Roll": {
        "slot": "roll",
        "anim_group": "a00",
        "required_fields": ["anim_id", "duration", "stamina_cost", "iframes_start", "iframes_end"],
        "notes": "DSR: przewrot = akcja w HKS + koszt wytrzymalosci w parametrach postaci.",
    },
    "ItemUse": {
        "slot": "item_use",
        "anim_group": "a00",
        "required_fields": ["anim_id", "duration", "cancel_window", "slot_mask"],
        "notes": "DSR: uzycie przedmiotu = osobny wariant HKS + maska slotow.",
    },
    "Step": {"slot": "step", "anim_group": "a00", "required_fields": ["anim_id", "duration"]},
    "Guard": {"slot": "guard", "anim_group": "a00", "required_fields": ["anim_id", "guard_break_stamina"]},
    "Attack": {"slot": "attack", "anim_group": "a00", "required_fields": ["anim_id", "behavior_id", "hitbox"]},
    "Magic": {"slot": "magic", "anim_group": "a00", "required_fields": ["anim_id", "cast_time"]},
    "Aim": {"slot": "aim", "anim_group": "a00", "required_fields": ["anim_id", "zoom_level"]},
    "Sheathe": {"slot": "sheathe", "anim_group": "a00", "required_fields": ["anim_id", "duration"]},
    "Death": {"slot": "death", "anim_group": "a00", "required_fields": ["anim_id"]},
    "Damage": {"slot": "damage", "anim_group": "a00", "required_fields": ["anim_id", "poise_break"]},
    "Idle": {"slot": "idle", "anim_group": "a00", "required_fields": ["anim_id"]},
}

# Stany, ktore DSR obsluguje "natywnie" i ktore maja sens przenosic w pierwszej kolejnosci.
CORE_ROLES = ("Jump", "Roll", "ItemUse")

# ---------------------------------------------------------------------------
# Pomocnicze: bajty, stringi, sciezki
# ---------------------------------------------------------------------------


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hexdump(data: bytes, length: int = 64) -> str:
    head = data[:length]
    return " ".join(f"{b:02x}" for b in head)


def printable(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def extract_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    """Zwraca liste (offset, tekst) dla stringow ASCII i UTF-16LE."""
    out: list[tuple[int, str]] = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        out.append((m.start(), m.group().decode("ascii")))
    # UTF-16LE - dekodujemy w oknach, zeby nie zgubic pozycji
    try:
        text = data.decode("utf-16-le", errors="ignore")
    except Exception:  # pragma: no cover
        text = ""
    for m in re.finditer(r"[\x20-\x7e]{%d,}" % min_len, text):
        out.append((m.start() * 2, m.group()))
    out.sort(key=lambda t: t[0])
    return out


# ---------------------------------------------------------------------------
# Warstwa DCX / BND
# ---------------------------------------------------------------------------


def decompress_entry(data: bytes) -> tuple[bytes, str]:
    """Rozpakuj pojedynczy wpis wewnatrz BND (ER trzyma je jako zstd)."""
    if not data:
        return data, "empty"
    magic = data[:4]
    if magic == b"\x28\xb5\x2f\xfd":
        try:
            return bndmod.zstd_decompress(data), "zstd"
        except Exception as exc:
            return data, f"zstd-failed:{exc}"
    if bndmod.is_dcx(data):
        try:
            return bndmod.dcx_decompress(data), "dcx"
        except Exception as exc:
            return data, f"dcx-failed:{exc}"
    return data, "raw"


def describe_magic(data: bytes) -> str:
    if len(data) < 4:
        return "too-short"
    magic = data[:4]
    if magic == b"\x28\xb5\x2f\xfd":
        return "zstd"
    if bndmod.is_dcx(data):
        return f"dcx:{magic.decode('latin-1')!r}"
    if magic == b"HKS " or magic == b"HKS\x00":
        return "HKS (skrypt behawioru)"
    if magic[:3] == b"HKX":
        return "HKX (dane Havoka)"
    if magic == b"\x00\x00\x00\x00":
        return "HKX-like (zerowy naglowek)"
    return f"raw:{magic.hex()}"


@dataclass
class ArchiveEntry:
    name: str
    data: bytes
    raw_size: int
    encoding: str
    sha: str

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass
class Archive:
    path: Path
    entries: list[ArchiveEntry] = field(default_factory=list)
    dcx_encoding: str = "none"
    notes: list[str] = field(default_factory=list)


def load_archive(path: Path) -> Archive:
    """Wczytaj archiwum BND lub rozpakowany folder z WitchyBND."""
    arch = Archive(path=path)

    # 1. Jesli istnieje folder z rozpakowana zawartoscia przez WitchyBND
    witchy_folder = path.parent / path.name.replace(".", "-")
    if not witchy_folder.is_dir():
        # Sprawdzamy rowniez wariant nazwy folderu bez rozszerzenia .dcx
        witchy_folder = path.parent / path.name.replace(".dcx", "").replace(".", "-")

    if witchy_folder.is_dir():
        arch.notes.append(f"wczytywanie z folderu WitchyBND: {witchy_folder.name}")
        for file_path in witchy_folder.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("_witchy"):
                payload = file_path.read_bytes()
                arch.entries.append(
                    ArchiveEntry(
                        name=file_path.name,
                        data=payload,
                        raw_size=len(payload),
                        encoding="raw_folder",
                        sha=sha256(payload),
                    )
                )
        return arch

    # 2. Jesli to plik binarny
    if not path.is_file():
        arch.notes.append(f"brak pliku lub folderu: {path}")
        return arch

    raw = path.read_bytes()

    if bndmod.is_dcx(raw):
        try:
            raw = bndmod.dcx_decompress(raw)
            arch.dcx_encoding = "dcx"
        except Exception:
            arch.notes.append("Pomijanie kompresji Kraken DCX - uzyj folderu WitchyBND")
            return arch

    if len(raw) < 0x10:
        arch.notes.append("plik za krotki na BND")
        return arch

    version, _flags = struct.unpack_from("<II", raw, 0)
    if version != 4:
        arch.notes.append(f"nieobslugiwana wersja BND: {version} (oczekiwano 4)")
        return arch

    try:
        container = bndmod.read_bnd4(raw)
    except Exception as exc:
        arch.notes.append(f"blad parsera BND4: {exc}")
        return arch

    for f in container.files:
        payload, encoding = decompress_entry(f.data)
        arch.entries.append(
            ArchiveEntry(
                name=f.name,
                data=payload,
                raw_size=len(f.data),
                encoding=encoding,
                sha=sha256(payload),
            )
        )
    return arch
# ---------------------------------------------------------------------------
# Analiza Havoka: klasy, sekcje, wersje
# ---------------------------------------------------------------------------


@dataclass
class HavokProfile:
    """Zbior faktov o pliku Havoka (HKX/HKS), uzywany do porownania."""

    label: str
    path: str = ""
    entry_name: str = ""
    size: int = 0
    magic: str = ""
    classes: list[str] = field(default_factory=list)
    tags: list[dict[str, Any]] = field(default_factory=list)
    version_markers: list[str] = field(default_factory=list)
    animation_objects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "entry": self.entry_name,
            "size": self.size,
            "magic": self.magic,
            "classes": self.classes,
            "class_count": len(self.classes),
            "sections": self.tags,
            "version_markers": self.version_markers,
            "animation_objects": self.animation_objects,
            "notes": self.notes,
        }


def extract_classes(data: bytes) -> list[str]:
    """Nazwy klas Havoka obecne w pliku (unikalne, posortowane)."""
    found = {m.group().decode("ascii") for m in _CLASS_RE.finditer(data)}
    return sorted(found)


def scan_hkx_sections(data: bytes, max_bytes: int = 8 * 1024 * 1024) -> list[dict[str, Any]]:
    """Skanuj plik w poszukiwaniu blokow z tagami 4-bajtowymi.

    Format HKX to sekcja tag + rozmiar; skaner jest odporny na wersje,
    bo rozpoznaje blok po warunku: 4 znaki alfanumeryczne + u32 rozmiar,
    ktorego zakres miesci sie w pliku.
    """
    limit = min(len(data), max_bytes)
    view = data[:limit]
    out: list[dict[str, Any]] = []
    for m in re.finditer(rb"[A-Z][A-Za-z0-9]{3}", view):
        pos = m.start()
        if pos + 8 > limit:
            continue
        tag = m.group().decode("ascii")
        size = struct.unpack_from("<I", view, pos + 4)[0]
        if size == 0 or size > len(data) - pos - 8:
            continue
        out.append(
            {
                "tag": tag,
                "known": KNOWN_HKX_TAGS.get(tag),
                "offset": pos,
                "size": size,
            }
        )
    return out


def detect_version_markers(data: bytes) -> list[str]:
    """Poszukaj w pliku oznak wersji Havoka / builda silnika."""
    markers: list[str] = []
    patterns = [
        rb"Havok[^\x00]{0,40}",
        rb"2010\.[0-9]",
        rb"HK[0-9]{4}[^\x00]{0,20}",
        rb"Physics20[0-9]{2}",
        rb"hk[A-Za-z0-9]*[ ]?version[^\x00]{0,20}",
    ]
    seen: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, data):
            text = m.group().decode("latin-1").strip()
            if text and text not in seen:
                seen.add(text)
                markers.append(text)
            if len(seen) > 60:
                break
    return sorted(markers)


def detect_animation_objects(data: bytes) -> list[str]:
    """Nazwy obiektow animacji (hkaAnimation, hkAnimatedNode, ...)."""
    names = {
        m.group().decode("ascii")
        for m in _CLASS_RE.finditer(data)
        if m.group().decode("ascii").lower().startswith(("hka", "hkn", "hkx"))
    }
    return sorted(names)


def profile_havok(label: str, path: str, entry_name: str, data: bytes) -> HavokProfile:
    prof = HavokProfile(
        label=label,
        path=path,
        entry_name=entry_name,
        size=len(data),
        magic=describe_magic(data),
    )
    prof.classes = extract_classes(data)
    prof.tags = scan_hkx_sections(data)
    prof.version_markers = detect_version_markers(data)
    prof.animation_objects = detect_animation_objects(data)
    if prof.magic.startswith("raw:") and not prof.classes:
        prof.notes.append("nie rozpoznano sygnatury HKX/HKS")
    return prof


def compare_profiles(er: HavokProfile, dsr: HavokProfile) -> dict[str, Any]:
    """Porownanie naglowkow klas Havoka: ER (2010.2) vs DSR (2010.1, x64)."""
    er_c, dsr_c = set(er.classes), set(dsr.classes)
    er_t = {t["tag"] for t in er.tags}
    dsr_t = {t["tag"] for t in dsr.tags}
    return {
        "only_in_er": sorted(er_c - dsr_c),
        "only_in_dsr": sorted(dsr_c - er_c),
        "shared_classes": len(er_c & dsr_c),
        "sections_only_in_er": sorted(er_t - dsr_t),
        "sections_only_in_dsr": sorted(dsr_t - er_t),
        "sections_shared": len(er_t & dsr_t),
        "er_version_markers": er.version_markers,
        "dsr_version_markers": dsr.version_markers,
    }


# ---------------------------------------------------------------------------
# HKS - graf zachowan
# ---------------------------------------------------------------------------


@dataclass
class HksState:
    index: int
    name: str
    offset: int = 0
    role: str = ""
    variant: str = ""
    transitions: list[dict[str, Any]] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class HksDocument:
    name: str
    size: int = 0
    magic: str = ""
    version: str = ""
    variants: list[str] = field(default_factory=list)
    states: list[HksState] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)
    confidence: str = "heuristic"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
            "magic": self.magic,
            "version": self.version,
            "confidence": self.confidence,
            "variants": self.variants,
            "variables": self.variables,
            "state_count": len(self.states),
            "states": [
                {
                    "index": s.index,
                    "name": s.name,
                    "role": s.role,
                    "variant": s.variant,
                    "offset": s.offset,
                    "transitions": s.transitions,
                    "attributes": s.attributes,
                }
                for s in self.states
            ],
            "notes": self.notes,
        }


def classify_role(name: str) -> str:
    for role, pat in ROLE_PATTERNS:
        if pat.search(name):
            return role
    return "Other"


def _read_cstring(data: bytes, pos: int, limit: int = 128) -> tuple[str, int]:
    end = data.find(b"\x00", pos, pos + limit)
    if end == -1:
        return "", pos
    try:
        return data[pos:end].decode("utf-8"), end + 1
    except UnicodeDecodeError:
        return data[pos:end].decode("latin-1"), end + 1


def parse_hks(data: bytes, name: str = "") -> HksDocument:
    """Analiza pliku HKS (skrypt behawioru gracza/wrogow).

    Format HKS nie jest udokumentowany publicznie. Skrypt:
      a) rozpoznaje naglowek ('HKS'),
      b) zbiera wszystkie stringi (tabela nazw stanow i zmiennych),
      c) probuje odczytac strukture "wariant -> stany -> przejscia"
         przy dwoch hipotezach ukladu naglowka i wybiera te, ktora
         waliduje sie (offsety w granicach pliku, stringi sensowne).
      Jesli zadna hipoteza nie przechodzi walidacji, zostaje tryb
      "heuristic" - sama inwentaryzacja nazw.
    """
    doc = HksDocument(name=name, size=len(data), magic=describe_magic(data))
    all_strings = [s for _off, s in extract_strings(data, min_len=3)]
    # unikalne, zachowujemy kolejnosc
    seen: set[str] = set()
    uniq: list[str] = []
    for s in all_strings:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    doc.strings = uniq

    # Wersja silnika: szukamy wzorca "HKS x.x" lub podobnego
    for s in uniq[:64]:
        if re.match(r"^HKS[\s_-]?\S{0,12}$", s):
            doc.version = s
            break

    # Zmienne / nazwy stanow: identyfikatory typu CamelCase / snake_case
    idents = [s for s in uniq if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-\.]{2,63}", s)]
    doc.variables = [s for s in idents if re.search(r"(var|flag|state|motion|param|ctrl)", s, re.I)]

    # Próba odczytu struktury stanów: szukamy bloków, w których po sobie
    # występują: u32 id, string nazwy, u32 liczba przejść, (u32 cel, u32 flagi)
    # Probujemy znaleźć "anchor" - pozycję, od której taki blok się zaczyna.
    states = _parse_state_table(data)
    if states:
        doc.states = states
        doc.confidence = "validated"
        doc.notes.append(
            f"rozpoznano {len(states)} stanow w {len({s.variant for s in states})} wariantach"
        )
    else:
        doc.confidence = "heuristic"
        doc.notes.append(
            "struktura stanow nie zwalidowana - raport na podstawie samych nazw stanow"
        )
        # Budujemy stany z nazw, ktore wygladaja jak identyfikatory stanu
        idx = 0
        for s in idents:
            role = classify_role(s)
            if role == "Other" and not re.search(r"(jump|roll|item|step|guard|attack)", s, re.I):
                continue
            doc.states.append(HksState(index=idx, name=s, role=role, variant="(nieznany)"))
            idx += 1
    return doc


def _parse_state_table(data: bytes) -> list[HksState]:
    """Szuka w pliku tabeli stanow; zwraca liste stanow (pusta = brak)."""
    results: list[HksState] = []
    # Sygnatura: ciag bajtow [u32][cstring][u32] gdzie cstring jest nazwa stanu.
    # Szukamy wszystkich wystapien "id + nazwa + liczba".
    candidates = 0
    for m in re.finditer(rb"[\x20-\x7e]{3,64}\x00", data):
        off = m.start()
        name = m.group()[:-1].decode("latin-1")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-\.]{2,63}", name):
            continue
        if classify_role(name) == "Other" and not re.search(
            r"(state|motion|jump|roll|item|step|guard|attack|locomotion)", name, re.I
        ):
            continue
        # id prawdopodobnie 4 bajty przed nazwa
        if off < 4:
            continue
        sid = struct.unpack_from("<i", data, off - 4)[0]
        if not (0 <= sid < 100000):
            continue
        # liczba przejsc 4 bajty po nazwie
        after = m.end()
        if after + 4 > len(data):
            continue
        n_trans = struct.unpack_from("<i", data, after)[0]
        if not (0 <= n_trans <= 256):
            continue
        candidates += 1
        transitions: list[dict[str, Any]] = []
        pos = after + 4
        ok = True
        for _ in range(n_trans):
            if pos + 8 > len(data):
                ok = False
                break
            target = struct.unpack_from("<i", data, pos)[0]
            flags = struct.unpack_from("<i", data, pos + 4)[0]
            if not (0 <= target < 100000):
                ok = False
                break
            transitions.append({"target": target, "flags": flags})
            pos += 8
        if not ok or not transitions:
            continue
        results.append(
            HksState(
                index=sid,
                name=name,
                offset=off - 4,
                role=classify_role(name),
                transitions=transitions,
            )
        )
    # Wymagamy >= 3 stanow zeby uwazyc tabele za zwalidowana
    return results if len(results) >= 3 else []


# ---------------------------------------------------------------------------
# Mapowanie na struktury DSR
# ---------------------------------------------------------------------------


def build_mapping(doc: HksDocument, dsr_doc: HksDocument | None) -> dict[str, Any]:
    """Zbuduj plan mapowania stanow ER -> sloty DSR."""
    next_id = 0x1000
    if dsr_doc and dsr_doc.states:
        next_id = max((s.index for s in dsr_doc.states), default=0) + 1

    mapped: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for st in doc.states:
        slot = DSR_STATE_SLOTS.get(st.role)
        if slot is None:
            unmatched.append(st.name)
            continue
        mapped.append(
            {
                "dsr_state_id": next_id,
                "dsr_slot": slot["slot"],
                "role": st.role,
                "er_state": st.name,
                "er_index": st.index,
                "er_variant": st.variant,
                "required_fields": slot["required_fields"],
                "notes": slot.get("notes", ""),
                "transitions": st.transitions,
            }
        )
        next_id += 1

    return {
        "target_engine": "Dark Souls Remastered (Havok 2010.1, 64-bit)",
        "source_engine": "Elden Ring (Havok 2010.2)",
        "core_roles": list(CORE_ROLES),
        "states": mapped,
        "unmapped_states": unmatched,
        "variant_note": (
            "Kazdy stan ER musi trafic do wariantu HSR odpowiadajacego "
            "rodzajowi broni (jednoraczna, dlaczlonostronna, dlonna) - "
            "liczba wariantow rozni sie miedzy ER a DSR."
        ),
    }


def build_adapter_plan(mapping: dict[str, Any]) -> dict[str, Any]:
    """Plan adaptera HKS: co trzeba zrobic, zeby DSR przyjal stany."""
    slots = sorted({s["dsr_slot"] for s in mapping["states"]})
    core = [s for s in mapping["states"] if s["role"] in CORE_ROLES]
    return {
        "step_1_layout": (
            "Wyciagnac docelowy HKS z DSR (chr/c0000.behbnd.dcx -> *.hks) i "
            "odczytac jego naglowek: liczba wariantow, rozmiar tabeli stanow, "
            "tabela stringow."
        ),
        "step_2_ids": (
            "Nowe stany dostaja identyfikatory z zakresu >= 0x1000, "
            "aby nie kolidowac z istniejacymi stanami DSR."
        ),
        "step_3_strings": (
            "Nazwy stanow trafiaja do tabeli stringow HKS (ta sama semantyka "
            "co w ER, ale wskazniki stringow sa 32-bitowe w obu wersjach)."
        ),
        "step_4_transitions": (
            "Przejscia mapujemy 1:1 na przejscia docelowego wariantu DSR; "
            "przejscia wskazujace stany nieobecne w DSR sa odrzucane."
        ),
        "step_5_havok": (
            "Struktury HKX (rig, animacje, controller) nie sa wspoldzielone "
            "miedzy wersjami Havoka - wymagaja konwersji przez konwerter "
            "HKX, nie przez podmiane bajtow."
        ),
        "slots_used": slots,
        "core_states": [
            {
                "role": s["role"],
                "dsr_state_id": s["dsr_state_id"],
                "dsr_slot": s["dsr_slot"],
                "er_state": s["er_state"],
                "required_fields": s["required_fields"],
            }
            for s in core
        ],
    }


# ---------------------------------------------------------------------------
# Raport
# ---------------------------------------------------------------------------


def write_report(
    out_dir: Path,
    er_beh: Archive,
    er_ani: Archive,
    er_beh_profiles: list[HavokProfile],
    er_ani_profiles: list[HavokProfile],
    dsr_beh: Archive | None,
    dsr_ani: Archive | None,
    dsr_beh_profiles: list[HavokProfile],
    dsr_ani_profiles: list[HavokProfile],
    er_doc: HksDocument,
    dsr_doc: HksDocument | None,
    mapping: dict[str, Any],
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    diffs: list[dict[str, Any]] = []
    if dsr_beh_profiles and er_beh_profiles:
        diffs.append(
            {
                "kind": "behabnd",
                "er_entry": er_beh_profiles[0].entry_name,
                "dsr_entry": dsr_beh_profiles[0].entry_name,
                **compare_profiles(er_beh_profiles[0], dsr_beh_profiles[0]),
            }
        )
    if dsr_ani_profiles and er_ani_profiles:
        diffs.append(
            {
                "kind": "anibnd",
                "er_entry": er_ani_profiles[0].entry_name,
                "dsr_entry": dsr_ani_profiles[0].entry_name,
                **compare_profiles(er_ani_profiles[0], dsr_ani_profiles[0]),
            }
        )

    payload = {
        "generated_by": "tools/convert_er_c0000_to_dsr.py",
        "er": {
            "behavior_archive": {
                "path": str(er_beh.path),
                "dcx": er_beh.dcx_encoding,
                "entries": [
                    {"name": e.name, "size": e.size, "raw_size": e.raw_size,
                     "encoding": e.encoding, "sha256": e.sha}
                    for e in er_beh.entries
                ],
                "notes": er_beh.notes,
            },
            "anim_archive": {
                "path": str(er_ani.path),
                "dcx": er_ani.dcx_encoding,
                "entry_count": len(er_ani.entries),
                "notes": er_ani.notes,
            },
            "behavior_profiles": [p.to_dict() for p in er_beh_profiles],
            "anim_profiles": [p.to_dict() for p in er_ani_profiles],
            "behavior_graph": er_doc.to_dict(),
        },
        "dsr": None,
        "havok_diff": diffs,
        "mapping": mapping,
    }
    if dsr_beh is not None:
        payload["dsr"] = {
            "behavior_archive": {
                "path": str(dsr_beh.path),
                "dcx": dsr_beh.dcx_encoding,
                "entries": [
                    {"name": e.name, "size": e.size, "encoding": e.encoding, "sha256": e.sha}
                    for e in dsr_beh.entries
                ],
                "notes": dsr_beh.notes,
            },
            "behavior_profiles": [p.to_dict() for p in dsr_beh_profiles],
            "anim_profiles": [p.to_dict() for p in dsr_ani_profiles],
            "behavior_graph": dsr_doc.to_dict() if dsr_doc else None,
        }

    p = out_dir / "havok_port_report.json"
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    written["report_json"] = p

    p = out_dir / "er_behavior_graph.json"
    p.write_text(json.dumps(er_doc.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    written["er_graph"] = p

    p = out_dir / "state_map_er_to_dsr.json"
    p.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    written["state_map"] = p

    p = out_dir / "dsr_adapter_plan.json"
    p.write_text(
        json.dumps(build_adapter_plan(mapping), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    written["adapter_plan"] = p

    # Raport tekstowy (markdown) - czytelny dla czlowieka
    lines: list[str] = []
    lines.append("# Havok: ER -> DSR - raport portu silnika postaci\n")
    lines.append(f"## 1. Archiwa\n")
    lines.append(f"- ER behavior: `{er_beh.path}` ({len(er_beh.entries)} wpisow, DCX={er_beh.dcx_encoding})")
    for e in er_beh.entries[:20]:
        lines.append(f"    - `{e.name}` {e.size} B ({e.encoding})")
    lines.append(f"- ER anim: `{er_ani.path}` ({len(er_ani.entries)} wpisow, DCX={er_ani.dcx_encoding})")
    lines.append("")
    lines.append("## 2. Naglowki klas Havoka\n")
    if diffs:
        for d in diffs:
            lines.append(f"### {d['kind']}: `{d['er_entry']}` vs `{d['dsr_entry']}`")
            lines.append(f"- wspoldzielone klasy: {d['shared_classes']}")
            lines.append(f"- tylko w ER: {len(d['only_in_er'])} -> {', '.join(d['only_in_er'][:12])}")
            lines.append(f"- tylko w DSR: {len(d['only_in_dsr'])} -> {', '.join(d['only_in_dsr'][:12])}")
            lines.append(f"- sekcje tylko w ER: {d['sections_only_in_er']}")
            lines.append(f"- sekcje tylko w DSR: {d['sections_only_in_dsr']}")
            lines.append(f"- oznaki wersji ER: {d['er_version_markers'][:8]}")
            lines.append(f"- oznaki wersji DSR: {d['dsr_version_markers'][:8]}")
            lines.append("")
    else:
        lines.append("- brak plikow DSR do porownania (uzyj --dsr-chr)\n")
    lines.append("## 3. Graf zachowan (ER)\n")
    lines.append(f"- rozpoznanie: **{er_doc.confidence}**")
    lines.append(f"- stany: {len(er_doc.states)}")
    lines.append(f"- warianty: {len(set(s.variant for s in er_doc.states))}")
    if er_doc.notes:
        for n in er_doc.notes:
            lines.append(f"- {n}")
    lines.append("")
    lines.append("## 4. Mapowanie stanow na sloty DSR\n")
    for s in mapping["states"][:40]:
        lines.append(
            f"- `{s['er_state']}` (ER #{s['er_index']}, rola {s['role']}) -> "
            f"DSR #{s['dsr_state_id']:04X} slot `{s['dsr_slot']}`"
        )
    if mapping["unmapped_states"]:
        lines.append(f"- niezmapowane: {len(mapping['unmapped_states'])} stanow")
    lines.append("")
    lines.append("## 5. Ograniczenia\n")
    lines.append(
        "- HKS/HKX nie maja publicznej specyfikacji; skrypt dziala heurystycznie "
        "i raportuje poziom pewnosci."
    )
    lines.append(
        "- Bloki HKX (rig, animacja, controller) wymagaja konwertera HKX "
        "miedzy Havok 2010.2 a 2010.1; sam HKS (graf zachowan) jest warstwa "
        "wlasna FromSoftware i portowalna."
    )
    lines.append(
        "- Skrypt nie zapisuje niczego w katalogach gier."
    )
    p = out_dir / "HAVOK_PORT_REPORT.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    written["report_md"] = p

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def find_archive(chr_dir: Path, names: Iterable[str]) -> Path | None:
    for n in names:
        p = chr_dir / n
        if p.exists():
            return p
    return None


def collect_profiles(arch: Archive, label: str) -> list[HavokProfile]:
    """Profil Havoka dla najwiekszych wpisow archiwum (animacje/komponenty)."""
    profs: list[HavokProfile] = []
    for e in sorted(arch.entries, key=lambda x: x.size, reverse=True)[:5]:
        if e.size == 0:
            continue
        profs.append(profile_havok(label, str(arch.path), e.name, e.data))
    return profs


def cmd_line_hint(er_chr: Path, dsr_chr: Path | None, out: Path) -> str:
    dsr = dsr_chr if dsr_chr else Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
    return (
        "CMD:\r\n"
        "  cd /d C:\\Users\\nemos\\workspace\\ds1-elden-port\r\n"
        f'  python tools\\convert_er_c0000_to_dsr.py --er-chr "{er_chr}" '
        f'--dsr-chr "{dsr}" --out "{out}"\r\n'
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Rozpakowuje c0000.behabnd.dcx / c0000.anibnd.dcx z ER, "
        "porownuje naglowki klas Havoka z DSR i mapuje stany (Jump/Roll/ItemUse)."
    )
    ap.add_argument("--er-chr", type=Path, default=DEFAULT_ER_CHR,
                    help="katalog z plikami ER (nuxe/chr)")
    ap.add_argument("--dsr-chr", type=Path, default=None,
                    help="katalog z plikami DSR (chr) - wymagany do porownania Havoka")
    ap.add_argument("--out", type=Path, default=Path("work/havok-port"),
                    help="katalog na wyniki")
    args = ap.parse_args(argv)

    print("=" * 72)
    print("ER -> DSR: konwerter silnika postaci (c0000)")
    print("=" * 72)

    # --- 1. Archiwa ER ---
    er_beh_path = find_archive(args.er_chr, ER_BEHAVIOR_NAMES)
    er_ani_path = find_archive(args.er_chr, ER_ANIM_NAMES)
    if er_beh_path is None or er_ani_path is None:
        print(f"[BLAD] Nie znaleziono c0000.behabnd.dcx / c0000.anibnd.dcx w {args.er_chr}")
        return 2
    print(f"[ER] behavior: {er_beh_path}")
    er_beh = load_archive(er_beh_path)
    print(f"     wpisow: {len(er_beh.entries)}, DCX: {er_beh.dcx_encoding}, notatki: {er_beh.notes}")
    print(f"[ER] anim:    {er_ani_path}")
    er_ani = load_archive(er_ani_path)
    print(f"     wpisow: {len(er_ani.entries)}, DCX: {er_ani.dcx_encoding}, notatki: {er_ani.notes}")

    # --- 2. Profile Havoka (ER) ---
    er_beh_profiles = collect_profiles(er_beh, "ER")
    er_ani_profiles = collect_profiles(er_ani, "ER")
    for p in er_beh_profiles[:3]:
        print(f"     HKS/HKX: {p.entry_name} {p.size} B, magic={p.magic}, "
              f"klas={len(p.classes)}, sekcje={len(p.tags)}")

    # --- 3. Archiwa DSR (opcjonalnie) ---
    dsr_beh = dsr_ani = None
    dsr_beh_profiles: list[HavokProfile] = []
    dsr_ani_profiles: list[HavokProfile] = []
    dsr_doc: HksDocument | None = None
    if args.dsr_chr and args.dsr_chr.exists():
        dsr_beh_path = find_archive(args.dsr_chr, ER_BEHAVIOR_NAMES)
        dsr_ani_path = find_archive(args.dsr_chr, ER_ANIM_NAMES)
        if dsr_beh_path:
            dsr_beh = load_archive(dsr_beh_path)
            dsr_beh_profiles = collect_profiles(dsr_beh, "DSR")
            print(f"[DSR] behavior: {dsr_beh_path} ({len(dsr_beh.entries)} wpisow)")
        if dsr_ani_path:
            dsr_ani = load_archive(dsr_ani_path)
            dsr_ani_profiles = collect_profiles(dsr_ani, "DSR")
            print(f"[DSR] anim:    {dsr_ani_path} ({len(dsr_ani.entries)} wpisow)")
    else:
        print("[DSR] pominieto (brak --dsr-chr) - porownanie Havoka nie zostanie wykonane")

    # --- 4. Graf zachowan ---
    er_doc = HksDocument(name="(ER)")
    for e in er_beh.entries:
        if e.size == 0:
            continue
        head = e.data[:4]
        if head.startswith(b"HKS"):
            doc = parse_hks(e.data, e.name)
            if len(doc.states) >= len(er_doc.states):
                er_doc = doc
                break
    if not er_doc.states and er_beh.entries:
        er_doc = parse_hks(max(er_beh.entries, key=lambda x: x.size).data, "ER (najwiekszy wpis)")
    print(f"[HKS] ER: {len(er_doc.states)} stanow, wariantow: "
          f"{len(set(s.variant for s in er_doc.states))}, pewnosc: {er_doc.confidence}")
    for n in er_doc.notes:
        print(f"       {n}")

    if dsr_beh:
        for e in dsr_beh.entries:
            if e.size and e.data[:4].startswith(b"HKS"):
                dsr_doc = parse_hks(e.data, e.name)
                break
        if dsr_doc:
            print(f"[HKS] DSR: {len(dsr_doc.states)} stanow, pewnosc: {dsr_doc.confidence}")

    # --- 5. Mapowanie ---
    mapping = build_mapping(er_doc, dsr_doc)
    core_hits = {s["role"] for s in mapping["states"]}
    missing = [r for r in CORE_ROLES if r not in core_hits]
    print(f"[MAP] zmapowanych stanow: {len(mapping['states'])}, "
          f"niezmapowanych: {len(mapping['unmapped_states'])}")
    print(f"[MAP] stany rdzeniowe (Jump/Roll/ItemUse): "
          f"{'OK' if not missing else 'BRAK -> ' + ', '.join(missing)}")

    # --- 6. Raporty ---
    written = write_report(
        args.out, er_beh, er_ani, er_beh_profiles, er_ani_profiles,
        dsr_beh, dsr_ani, dsr_beh_profiles, dsr_ani_profiles,
        er_doc, dsr_doc, mapping,
    )
    print("[OUT]")
    for k, v in written.items():
        print(f"     {k}: {v}")

    print()
    print(cmd_line_hint(args.er_chr, args.dsr_chr, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
