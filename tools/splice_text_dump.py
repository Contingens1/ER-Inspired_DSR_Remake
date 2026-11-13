"""Wkleja zrzut odszyfrowanej sekcji .text (z er_engine.dll) do KOPII exe DSR.

Arxan trzyma czesc kodu zaszyfrowana na dysku, wiec Ghidra na oryginalnym exe widzi losowe
bajty. Kopia z wklejonym zrzutem jest normalnym plikiem PE do analizy (nie do uruchamiania).

Uzycie:
    python tools\\splice_text_dump.py --exe "F:\\...\\DarkSoulsRemastered.exe" ^
        --dump dist\\mods\\c0000_er_engine\\bin\\text_dump_6344d056.bin --out work\\ghidra\\DSR_decrypted.exe
"""
import argparse
import struct
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True, type=Path)
    ap.add_argument("--dump", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    if a.out.resolve() == a.exe.resolve():
        raise SystemExit("BLAD: --out nie moze nadpisac oryginalnego exe.")
    data = bytearray(a.exe.read_bytes())
    dump = a.dump.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    sec = pe + 24 + opt  # pierwsza sekcja = .text
    name, vsize, rva, rsize, rptr = struct.unpack_from("<8sIIII", data, sec)
    if name.rstrip(b"\0") != b".text" or len(dump) != vsize:
        raise SystemExit(f"BLAD: zrzut {len(dump)} B nie pasuje do sekcji {name!r} ({vsize:#x} B).")
    n = min(vsize, rsize)
    changed = sum(1 for i in range(0, n, 0x1000) if data[rptr + i:rptr + i + 0x1000] != dump[i:i + 0x1000])
    data[rptr:rptr + n] = dump[:n]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(data)
    print(f"wklejono .text: {changed} stron 4 KB rozni sie od pliku na dysku -> {a.out}")


if __name__ == "__main__":
    main()
