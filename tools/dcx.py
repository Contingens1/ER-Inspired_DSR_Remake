"""
dcx.py - Dekoder kompresji DCX używanej przez pliki FromSoftware (Bandai Namco / FromSoftware).

Format DCX: nagłówek 4 bajty (m.in. 'Dcx\\x00' lub 'DFL\0' dla DS1 Remastered)
plus seria bloków z własnym nagłówkiem. Każdy blok to zlib stream z lub bez
krótkiego prefiksu w nagłówku bloku.

Obsługiwane warianty:
  - Dcx\\x00  (ogólny, np. param/GameParam, paramdef)
  - DFL\\x00  (ten sam schemat blokowy, używany w DS1 Remastered dla *.bnd)
  - Dcx\\x01 / x02 (kontener z zewnętrznym nagłówkiem + bloki)

Autor: rekonesans dla projektu portu mechaniki walki ER -> DS1.
"""

from __future__ import annotations

import struct
import zlib
from typing import Iterator

# Nagłówki DCX, które traktujemy jako "kontener blokowy".
_BLOCK_MAGICS = (b"Dcx\x00", b"DFL\x00", b"DCX\x00")

# Zmienne nagłówka zewnętrznego (offset bloku, kompresja itp.) w zależności
# od wariantu. Trzymamy to w tabeli, bo każdy wariant ma inną semantykę.
_DCX_X01 = b"Dcx\x01"
_DCX_X02 = b"Dcx\x02"

_CHUNK_SIZE = 0x10000


class DcxError(Exception):
    """Błąd dekodowania DCX."""


def _decompress_block(payload: bytes) -> bytes:
    """Rozpakuj jeden blok zlib."""
    try:
        return zlib.decompress(payload)
    except zlib.error:
        # Niektóre bloki mają zły nagłówek zlib (np. 4 bajty prefiksu).
        # Spróbujmy surowego inflate i od zera.
        for start in (2, 1, 4):
            try:
                d = zlib.decompressobj(-zlib.MAX_WBITS)
                out = d.decompress(payload[start:])
                if out:
                    return out
            except zlib.error:
                continue
        # Ostatecznie: surowy deflate od początku bez okna.
        try:
            d = zlib.decompressobj(-zlib.MAX_WBITS)
            return d.decompress(payload)
        except zlib.error as exc:
            raise DcxError(f"Nie mozna rozpakowac bloku DCX: {exc}") from exc


def _parse_block_stream(data: bytes) -> Iterator[bytes]:
    """Zdekompresuj sekwencje blokow DCX zaczynajac sie od offsetu 0.

    Zwraca kolejne fragmenty (kolejne 'chunki') jako bajty.
    """
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
        if payload_end > len(data):
            # Ostatni blok bywa przyciety - dekompresujemy co jest.
            payload = data[payload_start:]
        else:
            payload = data[payload_start:payload_end]
        raw = _decompress_block(payload)
        if uncompressed_size and len(raw) != uncompressed_size:
            raw = raw[:uncompressed_size]
        yield raw
        pos = payload_end


def decompress(data: bytes) -> bytes:
    """Zdekompresuj plik DCX i zwroc pelna tresc.

    Zwraca `data` bez zmian, jesli nie jest to DCX.
    """
    if len(data) < 8:
        return data

    magic = data[:4]

    if magic in _BLOCK_MAGICS:
        return b"".join(_parse_block_stream(data[4:]))

    if magic == _DCX_X01:
        # Naglowek: 'Dcx\x01', offset do blokow (u32), rozmiar danych.
        offset = struct.unpack_from("<I", data, 4)[0]
        return b"".join(_parse_block_stream(data[offset:]))

    if magic == _DCX_X02:
        # Naglowek: 'Dcx\x02', offset do blokow (u32), rozmiar danych (u32).
        offset = struct.unpack_from("<I", data, 4)[0]
        return b"".join(_parse_block_stream(data[offset:]))

    return data


def is_dcx(data: bytes) -> bool:
    """Czy plik jest opakowany w DCX?"""
    return data[:4] in _BLOCK_MAGICS or data[:4] in (_DCX_X01, _DCX_X02)


def compress(data: bytes) -> bytes:
    """Zapakuj dane do DCX w wariancie 'Dcx\\x00' (domyslny dla paramow)."""
    out = bytearray(b"Dcx\x00")
    # Naglowek DCX x00: 4 bajty rozmiaru (czescowo wazniona) + flagi.
    body = bytearray()
    for i in range(0, len(data), _CHUNK_SIZE):
        chunk = data[i : i + _CHUNK_SIZE]
        comp = zlib.compress(chunk, 9)
        header = struct.pack("<HHII", 0x10, len(comp), len(chunk), 0)
        body += header + comp
    # Trailing: naglowek pustego bloku.
    body += struct.pack("<HHII", 0x10, 0, 0, 0)
    out += struct.pack("<H", len(out) + 4)  # rozmiar naglowka (czescowo wazniony)
    out += body
    return bytes(out)
