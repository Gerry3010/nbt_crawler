import io
import zlib
import struct
from pathlib import Path

import anvil
import nbtlib


# ─────────────────────────────────────────────
#  Low-level Region I/O
# ─────────────────────────────────────────────

def _chunk_header_offset(cx: int, cz: int) -> int:
    return 4 * ((cx % 32) + (cz % 32) * 32)


def read_chunk_nbt(region_path: Path, cx: int, cz: int) -> nbtlib.File | None:
    """
    Liest den Chunk (cx, cz) aus einer Region-File.
    Gibt None zurück wenn der Chunk nicht existiert.
    """
    with open(region_path, "rb") as f:
        f.seek(_chunk_header_offset(cx, cz))
        loc = struct.unpack(">I", f.read(4))[0]
        offset = (loc >> 8) * 4096

        if offset == 0:
            return None

        f.seek(offset)
        length = struct.unpack(">I", f.read(4))[0]
        compression = struct.unpack("B", f.read(1))[0]
        compressed = f.read(length - 1)

    if compression != 2:
        raise ValueError(f"Unbekannte Compression type: {compression}")

    return nbtlib.File.parse(io.BytesIO(zlib.decompress(compressed)))


def write_chunk_nbt(region_path: Path, cx: int, cz: int, nbt_data: nbtlib.File) -> bool:
    """
    Schreibt ein mutiertes NBT-Compound zurück in die Region-File.
    Gibt False zurück wenn der neue Chunk nicht in den alten Slot passt.
    ACHTUNG: Welt muss offline sein!
    """
    buf = io.BytesIO()
    nbt_data.write(buf)
    compressed = zlib.compress(buf.getvalue())

    with open(region_path, "r+b") as f:
        f.seek(_chunk_header_offset(cx, cz))
        loc = struct.unpack(">I", f.read(4))[0]
        offset = (loc >> 8) * 4096
        old_max_bytes = (loc & 0xFF) * 4096 - 5  # minus length+compression header

        if len(compressed) > old_max_bytes:
            print(f"  ⚠️  Chunk zu groß! {len(compressed)} > {old_max_bytes} bytes")
            return False

        f.seek(offset)
        f.write(struct.pack(">I", len(compressed) + 1))
        f.write(struct.pack("B", 2))  # zlib
        f.write(compressed)

    return True


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _block_to_chunk(bx: int, bz: int) -> tuple[int, int]:
    return bx >> 4, bz >> 4


def _get_region_path(world_path: Path, cx: int, cz: int) -> Path:
    rx, rz = cx >> 5, cz >> 5
    return world_path / "region" / f"r.{rx}.{rz}.mca"


# ─────────────────────────────────────────────
#  Quark Chest → Vanilla Chest Konvertierung
# ─────────────────────────────────────────────

def convert_quark_chest(world_path: Path, chest: dict) -> bool:
    """
    Konvertiert eine einzelne Quark Chest zu einer Vanilla Chest.
    Ändert sowohl die Block Entity ID als auch den Blockstate in der Palette.
    """
    bx, by, bz = chest["x"], chest["y"], chest["z"]
    cx, cz = _block_to_chunk(bx, bz)
    region_path = _get_region_path(world_path, cx, cz)

    nbt_data = read_chunk_nbt(region_path, cx, cz)
    if nbt_data is None:
        print(f"  ⚠️  Chunk nicht gefunden für X={bx} Y={by} Z={bz}")
        return False

    # Block Entity ID patchen
    found = False
    for be in nbt_data["block_entities"]:
        if be["x"] == bx and be["y"] == by and be["z"] == bz:
            print(f"  ✅ {be['id']} → minecraft:chest @ X={bx} Y={by} Z={bz}")
            be["id"] = nbtlib.String("minecraft:chest")
            found = True
            break

    if not found:
        print(f"  ⚠️  Block Entity nicht gefunden @ X={bx} Y={by} Z={bz}")
        return False

    # Blockstate Palette patchen
    for section in nbt_data["sections"]:
        if "block_states" not in section:
            continue
        for entry in section["block_states"].get("palette", []):
            name = entry.get("Name")
            if name is not None and name.startswith("quark:") and "chest" in name.lower():
                entry["Name"] = nbtlib.String("minecraft:chest")

    return write_chunk_nbt(region_path, cx, cz, nbt_data)


def convert_all_quark_chests(world_path: Path, parsed_entities: list[dict]) -> None:
    """
    Konvertiert alle Quark Chests aus dem Parse-Result zu Vanilla Chests.
    """
    quark_chests = [e for e in parsed_entities if e["is_quark_chest"]]

    if not quark_chests:
        print("Keine Quark Chests gefunden.")
        return

    print(f"\n🗃️  Konvertiere {len(quark_chests)} Quark Chest(s)...")
    success = sum(convert_quark_chest(world_path, c) for c in quark_chests)
    print(f"\n✅ {success}/{len(quark_chests)} Quark Chests konvertiert.")