"""
bnd.py - Czytnik i (opcjonalnie) pisarz archiwów FromSoftware: BND3/BND4, DCX, PARAM.

Formaty obsługiwane:
  - DCX: 'Dcx\\x00', 'DFL\\x00', 'Dcx\\x01', 'Dcx\\x02' (nagłówek + bloki zlib)
  - BND4: nagłówek 0x10 bajtów, tablica plików z nazwami UTF-16, bloki ZSTD
  - BND3: starszy nagłówek, nazwy ASCII z dopełnieniem
  - PARAM: typy podstawowe (SByte/Byte/Int16/UInt16/Int32/UInt32/Int64/UInt64/
    Single/Double), w tym wariant "wide" (RefType z 2-bajtowym polem typu)

Autor: rekonesans dla projektu "Souls Stance & Combat Overhaul" (ER -> DS1).
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# DCX
# ---------------------------------------------------------------------------

_BLOCK_MAGICS = (b"Dcx\x00", b"DFL\x00", b"DCX\x00")
_CHUNK_SIZE = 0x10000


class DcxError(Exception):
    pass


def _decompress_block(payload: bytes) -> bytes:
    try:
        return zlib.decompress(payload)
    except zlib.error:
        for start in (2, 1, 4):
            try:
                d = zlib.decompressobj(-zlib.MAX_WBITS)
                out = d.decompress(payload[start:])
                if out:
                    return out
            except zlib.error:
                continue
        try:
            d = zlib.decompressobj(-zlib.MAX_WBITS)
            return d.decompress(payload)
        except zlib.error as exc:
            raise DcxError(f"nie mozna rozpakowac bloku DCX: {exc}") from exc


def _parse_block_stream(data: bytes):
    pos = 0
    while pos + 8 <= len(data):
        header_size = struct.unpack_from("<H", data, pos)[0]
        if header_size < 0x10 or pos + header_size > len(data):
            break
        compressed_size = struct.unpack_from("<H", data, pos + 2)[0]
        uncompressed_size = struct.unpack_from("<I", data, pos + 4)[0]
        if compressed_size == 0:
            break
        payload_start = pos + header_size
        payload_end = payload_start + compressed_size
        payload = data[payload_start:] if payload_end > len(data) else data[payload_start:payload_end]
        raw = _decompress_block(payload)
        if uncompressed_size and len(raw) != uncompressed_size:
            raw = raw[:uncompressed_size]
        yield raw
        pos = payload_end


def dcx_decompress(data: bytes) -> bytes:
    """Zdekompresuj DCX; zwraca dane bez zmian, jeśli to nie DCX."""
    if len(data) < 8:
        return data
    magic = data[:4]
    if magic in _BLOCK_MAGICS:
        return b"".join(_parse_block_stream(data[4:]))
    if magic in (b"Dcx\x01", b"Dcx\x02"):
        offset = struct.unpack_from("<I", data, 4)[0]
        return b"".join(_parse_block_stream(data[offset:]))
    return data


def is_dcx(data: bytes) -> bool:
    return data[:4] in _BLOCK_MAGICS or data[:4] in (b"Dcx\x01", b"Dcx\x02")


# ---------------------------------------------------------------------------
# ZSTD (z stdlib Pythona 3.14+; fallback na zstandard)
# ---------------------------------------------------------------------------

def zstd_decompress(data: bytes, size: int = 0) -> bytes:
    try:
        from compression import zstd

        return zstd.decompress(data)
    except ImportError:
        pass
    try:
        import zstandard
    except ImportError as exc:  # pragma: no cover
        raise DcxError("brak obslugi zstd (compression.zstd lub zstandard)") from exc
    ctx = zstandard.ZstdDecompressor()
    if size:
        return ctx.decompress(data, max_output_size=size)
    return ctx.decompress(data, max_output_size=0x10000000)


def zstd_compress(data: bytes, level: int = 19) -> bytes:
    try:
        from compression import zstd

        return zstd.compress(data, level)
    except ImportError:
        import zstandard

    return zstandard.ZstdCompressor(level=level).compress(data)


# ---------------------------------------------------------------------------
# BND4
# ---------------------------------------------------------------------------

@dataclass
class BndFile:
    name: str
    data: bytes
    # pozycje w naglowku (do round-trip)
    id: int = 0
    offset: int = 0
    size: int = 0
    unknown: int = 0


@dataclass
class Bnd4:
    version: int = 4
    flags: int = 0
    files: list[BndFile] = field(default_factory=list)
    # bajty naglowka, ktore nalezy zachowac przy ponownym zapisie
    header_extra: bytes = b""

    def get(self, name: str) -> BndFile | None:
        low = name.lower()
        for f in self.files:
            if f.name.lower() == low:
                return f
        return None


def read_bnd4(data: bytes) -> Bnd4:
    """Parsuj archiwum BND4 (bez obslugi DCX - decompresja w callerze)."""
    if len(data) < 0x10:
        raise DcxError("za krotki plik na BND4")
    version, flags = struct.unpack_from("<II", data, 0)
    if version != 4:
        raise DcxError(f"nieobslugiwana wersja BND: {version}")

    file_count = struct.unpack_from("<I", data, 8)[0]
    # offset 0x0C: bajty "extra" (np. hashy w nowszych wersjach) - pomijamy
    # pozycje plikow zaczynaja sie od 0x10 + dlugosc extra
    # W standardowym BND4 header ma 0x10 bajtow i pliki sa liczone od 0x10.
    # Jednak niektore buildy maja "data offset" - odczytujemy z naglowka.
    data_offset = struct.unpack_from("<I", data, 0x0C)[0]
    if data_offset < 0x10 or data_offset > len(data):
        data_offset = 0x10

    files: list[BndFile] = []
    pos = 0x10
    for _ in range(file_count):
        if pos + 0x10 > len(data):
            break
        file_id, offset, size, unknown = struct.unpack_from("<iIII", data, pos)
        pos += 0x10
        # nazwa: UTF-16LE, 4-bajtowy prefiks dlugosci (incl. null) w niektorych
        # wariantach; odczytujemy null-terminated UTF-16 string.
        name_bytes = bytearray()
        while pos + 1 < len(data):
            ch = data[pos : pos + 2]
            if ch == b"\x00\x00":
                pos += 2
                break
            name_bytes += ch
            pos += 2
        name = name_bytes.decode("utf-16-le", errors="replace")
        files.append(
            BndFile(name=name, data=data[offset : offset + size], id=file_id, offset=offset, size=size, unknown=unknown)
        )
    return Bnd4(version=version, flags=flags, files=files, header_extra=data[0x10:data_offset])


def write_bnd4(bnd: Bnd4) -> bytes:
    """Zapisz BND4 (bez kompresji DCX/ZSTD - zwracamy surowy binder)."""
    # naglowek 0x10 bajtow
    header = struct.pack("<IIII", 4, bnd.flags, len(bnd.files), 0x10)
    # najpierw nazwy, potem dane
    name_block = bytearray()
    entries = bytearray()
    for f in bnd.files:
        entry = struct.pack("<iIII", f.id, 0, f.size, f.unknown)
        entries += entry
        enc = f.name.encode("utf-16-le") + b"\x00\x00"
        name_block += enc
        # wyrównanie do 4 bajtow dla naglowka pliku
        while len(name_block) % 4:
            name_block += b"\x00"
    data_block = bytearray()
    offset = 0x10 + len(entries) + len(name_block)
    new_entries = bytearray()
    for f in bnd.files:
        new_entries += struct.pack("<iIII", f.id, offset, len(f.data), f.unknown)
        data_block += f.data
        offset += len(f.data)
    return bytes(header) + bytes(new_entries) + bytes(name_block) + bytes(data_block)


# ---------------------------------------------------------------------------
# PARAM
# ---------------------------------------------------------------------------

PARAM_TYPES = {
    "sbyte": "b", "byte": "B", "short": "h", "ushort": "H",
    "int": "i", "uint": "I", "long": "q", "ulong": "Q",
    "float": "f", "double": "d",
}
# aliasy wystepujace w paramdefach
PARAM_TYPE_ALIASES = {
    "sbyte": "sbyte", "byte": "byte", "short": "short", "ushort": "ushort",
    "int": "int", "uint": "uint", "long": "long", "ulong": "ulong",
    "float": "float", "double": "double",
    "s8": "sbyte", "u8": "byte", "i16": "short", "u16": "ushort",
    "i32": "int", "u32": "uint", "i64": "long", "u64": "ulong",
    "f32": "float", "f64": "double",
}

# rozmiary w bajtach
_PARAM_SIZE = {
    "sbyte": 1, "byte": 1, "short": 2, "ushort": 2,
    "int": 4, "uint": 4, "long": 8, "ulong": 8, "float": 4, "double": 8,
}

# Rodzaje pol: wartosc zwykla, referencja (ID), bitfield, padding
PARAM_KIND_VALUE = 0
PARAM_KIND_REF = 1
PARAM_KIND_BITFIELD = 2
PARAM_KIND_PADDING = 3


@dataclass
class ParamField:
    name: str
    type: str
    kind: int = PARAM_KIND_VALUE
    ref_type: str | None = None   # typ referencji dla pola-ref
    array_size: int = 0
    bit_count: int = 0
    bit_offset: int = 0
    # flagi
    use_wide: bool = False       # 2-bajtowe pole typu (RefType)
    is_array: bool = False
    array_count: int = 0

    @property
    def size(self) -> int:
        base = _PARAM_SIZE.get(self.type, 4)
        if self.kind == PARAM_KIND_BITFIELD:
            return base
        if self.kind == PARAM_KIND_PADDING:
            return base
        if self.is_array:
            return base * max(1, self.array_count)
        return base


@dataclass
class ParamRow:
    id: int
    values: dict[str, Any] = field(default_factory=dict)
    # bajty wskaznikow (RefType) w kolejnosci wystapienia
    refs: dict[str, int] = field(default_factory=dict)
    cell_flags: dict[str, int] = field(default_factory=dict)


@dataclass
class Param:
    name: str
    fields: list[ParamField]
    rows: list[ParamRow]
    detype: str = ""
    # bajty naglowka PARAM (poza licznikiem wierszy)
    header_extra: bytes = b""
    param_type: int = 0
    row_size: int = 0
    # bajty "string table" - wartosci stringow (RefType = string)
    strings: dict[str, int] = field(default_factory=dict)


def _read_field_name(data: bytes, pos: int) -> tuple[str, int]:
    """Czytaj nazwe pola: bajt dlugosci + znaki (w paramach DS3/ER bywa UTF-16)."""
    if pos >= len(data):
        return "", pos
    length = data[pos]
    pos += 1
    if pos + length > len(data):
        return "", pos
    raw = data[pos : pos + length]
    pos += length
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-16-le", errors="replace")
    return text, pos


def parse_param(data: bytes, name: str = "") -> Param:
    """Parsuj plik PARAM ( SoulsFormats/FSParam)."""
    if len(data) < 0x10:
        raise DcxError("za krotki plik PARAM")
    param_type = struct.unpack_from("<I", data, 0)[0]
    row_size = struct.unpack_from("<H", data, 4)[0]
    row_count = struct.unpack_from("<H", data, 6)[0] & 0x7FFF
    if param_type == 0:
        row_count = struct.unpack_from("<I", data, 8)[0]
        # naglowek: type, row_size, row_count(4), string table size...
        str_size = struct.unpack_from("<I", data, 0x0C)[0]
        data_start = 0x10
    else:
        # naglowek 0x10 + string table + naglowek pol
        str_size = struct.unpack_from("<I", data, 0x08)[0]
        data_start = 0x10 + str_size

    # --- naglowek pol (detype) ---
    detype_size = struct.unpack_from("<I", data, data_start)[0]
    detype = data[data_start + 4 : data_start + 4 + detype_size]
    fields: list[ParamField] = []
    pos = data_start + 4 + detype_size
    # wskazniki stringow z naglowka pol
    field_count = struct.unpack_from("<H", data, pos)[0]
    pos += 2
    for _ in range(field_count):
        ftype = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        # rozmiar tablicy
        array_size = 0
        is_array = False
        if ftype in (0x08, 0x09):  # array of 32/8 bit
            array_size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            is_array = True
        # nazwa pola + flagi
        field_name, pos = _read_field_name(data, pos)
        # dlugosc nazwy w bajtach: 0xFF = 2-bajtowa flaga (bitfield) itd.
        # typy rozszerzone: 0x02 (bitfield), 0x03 (padding)
        base_type = ftype & 0x0F
        if ftype in (0x0E, 0x0F):  # ref type
            base_type = 0x0F
        kind = PARAM_KIND_VALUE
        ref_type = None
        bit_count = 0
        bit_offset = 0
        use_wide = False

        if ftype == 0x02:  # bitfield (wskaznik + maska)
            kind = PARAM_KIND_BITFIELD
            ref_id = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            bit_offset = ref_id >> 4
            bit_count = (ref_id & 0x0F) + 1
        elif ftype == 0x03:  # padding
            kind = PARAM_KIND_PADDING
        elif ftype in (0x0E, 0x0F):  # referencja (RefType)
            kind = PARAM_KIND_REF
            use_wide = ftype == 0x0F
            # po 4 bajtach ID + nazwa typu ref
            ref_id = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            ref_name, pos = _read_field_name(data, pos)
            ref_type = ref_name

        base = {0: "sbyte", 1: "byte", 2: "short", 3: "ushort",
                4: "int", 5: "uint", 6: "long", 7: "ulong",
                8: "float", 9: "double"}.get(base_type, "int")
        if kind == PARAM_KIND_REF:
            base = {0: "sbyte", 1: "byte", 2: "short", 3: "ushort",
                    4: "int", 5: "uint", 6: "long", 7: "ulong",
                    8: "float", 9: "double"}.get(base_type, "int")

        fields.append(
            ParamField(
                name=field_name,
                type=base,
                kind=kind,
                ref_type=ref_type,
                array_size=array_size if is_array else 0,
                is_array=is_array,
                array_count=array_size if is_array else 0,
                bit_count=bit_count,
                bit_offset=bit_offset,
                use_wide=use_wide,
            )
        )
        # wyrownanie do 4 bajtow po naglowku pol
    # po polach: tabela stringow
    str_table_end = data_start + str_size
    strings: dict[str, int] = {}
    # odczytujemy stringi z tabeli (po offsetach wskazywanych przez pola)
    # najprościej: zapisujemy surowy obszar i mapujemy offset->tekst
    string_area = data[data_start + 4 + detype_size : str_table_end]

    # --- wiersze ---
    rows: list[ParamRow] = []
    row_off = str_table_end
    for i in range(row_count):
        row_data = data[row_off : row_off + row_size]
        row_off += row_size
        if len(row_data) < row_size:
            break
        row = _parse_row(row_data, fields, string_area)
        rows.append(row)

    return Param(
        name=name,
        fields=fields,
        rows=rows,
        detype=detype.decode("utf-8", errors="replace").rstrip("\x00"),
        header_extra=data[0x10:data_start],
        param_type=param_type,
        row_size=row_size,
        strings=strings,
    )


def _parse_row(row_data: bytes, fields: list[ParamField], string_area: bytes) -> ParamRow:
    """Parsuj pojedynczy wiersz PARAM."""
    # ID wiersza: 4 bajty (s32) + 4 bajty paddingu (wazne dla 'wide')
    row_id = struct.unpack_from("<i", row_data, 0)[0]
    pos = 8
    values: dict[str, Any] = {}
    refs: dict[str, int] = {}
    cell_flags: dict[str, int] = {}
    for f in fields:
        if f.kind == PARAM_KIND_BITFIELD:
            base = f.type
            code = PARAM_TYPES.get(base, "i")
            if f.array_size:
                arr = []
                for _ in range(f.array_size):
                    arr.append(struct.unpack_from("<" + code, row_data, pos)[0])
                    pos += struct.calcsize(code)
                values[f.name] = arr
            else:
                raw = struct.unpack_from("<" + code, row_data, pos)[0]
                pos += struct.calcsize(code)
                # wyciagnij bity
                val = (raw >> f.bit_offset) & ((1 << f.bit_count) - 1)
                values[f.name] = val
        elif f.kind == PARAM_KIND_REF:
            # najpierw ID (4 bajty), potem wskaznik do stringa
            base = f.type
            code = PARAM_TYPES.get(base, "i")
            size = struct.calcsize(code)
            raw = struct.unpack_from("<" + code, row_data, pos)[0]
            pos += size
            values[f.name] = raw
            if f.use_wide:
                # 2 bajty dlugosc + bajty tekstu
                slen = struct.unpack_from("<H", row_data, pos)[0]
                pos += 2
                text = row_data[pos : pos + slen].decode("utf-8", errors="replace")
                pos += slen
                values[f.name + "__str"] = text
            else:
                # 4 bajty: bajt flagi + 3 bajty offsetu w string_area
                str_off = struct.unpack_from("<I", row_data, pos)[0]
                pos += 4
                # odczyt tekstu ze string_area
                if str_off < len(string_area):
                    end = string_area.find(b"\x00", str_off)
                    if end == -1:
                        end = len(string_area)
                    text = string_area[str_off:end].decode("utf-8", errors="replace")
                else:
                    text = ""
                values[f.name + "__str"] = text
                refs[f.name] = str_off
        elif f.kind == PARAM_KIND_PADDING:
            pos += f.size
        else:
            base = f.type
            code = PARAM_TYPES.get(base, "i")
            size = struct.calcsize(code)
            if f.is_array:
                arr = []
                for _ in range(f.array_size):
                    arr.append(struct.unpack_from("<" + code, row_data, pos)[0])
                    pos += size
                values[f.name] = arr
            else:
                values[f.name] = struct.unpack_from("<" + code, row_data, pos)[0]
                pos += size
    return ParamRow(id=row_id, values=values, refs=refs, cell_flags=cell_flags)
