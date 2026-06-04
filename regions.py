import anvil
from pathlib import Path


def block_to_chunk(bx: int, bz: int) -> tuple[int, int]:
    return bx >> 4, bz >> 4


def chunk_to_region(cx: int, cz: int) -> tuple[int, int]:
    return cx >> 5, cz >> 5  # = cx // 32


def get_chunks_in_radius(center_x: float, center_z: float, radius: int) -> set[tuple[int, int]]:
    """Gibt alle Chunk-Koordinaten im Chebyshev-Radius zurück"""
    cx, cz = block_to_chunk(int(center_x), int(center_z))

    chunks = set()
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            chunks.add((cx + dx, cz + dz))

    return chunks


def get_required_regions(chunks: set[tuple[int, int]]) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """Gruppiert Chunks nach ihrer Region → {(rx,rz): [(cx,cz), ...]}"""
    regions: dict[tuple[int, int], list[tuple[int, int]]] = {}

    for cx, cz in chunks:
        region_key = chunk_to_region(cx, cz)
        regions.setdefault(region_key, []).append((cx, cz))

    return regions

#
# Block Entity Helper für Regionen
#

def scan_region(
        region_path: Path,
        chunks_to_scan: list[tuple[int, int]]
) -> list[dict]:
    """
    Scannt gegebene Chunks in einem Region File.
    Gibt die Liste aller Block Entities zurück.
    """
    if not region_path.exists():
        return []  # Region existiert nicht (ungeladen) → überspringen

    region = anvil.Region.from_file(str(region_path))
    found = []

    for cx, cz in chunks_to_scan:
        # Lokale Chunk-Koordinaten innerhalb der Region (0-31)
        local_cx = cx % 32
        local_cz = cz % 32

        try:
            chunk = region.get_chunk(local_cx, local_cz)
        except Exception:
            continue  # Chunk noch nicht generiert → überspringen

        block_entities = chunk.data.get("block_entities", [])

        for be in block_entities:
            found.append({
                "id": str(be.get("id", "")),
                "x": be["x"].value,
                "y": be["y"].value,
                "z": be["z"].value,
                "nbt": be  # komplettes NBT für später
            })

    return found


def scan_world_radius(
        world_path: Path,
        center_x: float,
        center_z: float,
        radius: int = 20  # 20 Chunks = 320 Blöcke
) -> list[dict]:
    chunks = get_chunks_in_radius(center_x, center_z, radius)
    regions = get_required_regions(chunks)
    region_dir = world_path / "region"

    all_entities = []

    for (rx, rz), chunk_list in regions.items():
        region_file = region_dir / f"r.{rx}.{rz}.mca"
        entities = scan_region(region_file, chunk_list)
        all_entities.extend(entities)
        print(f"  r.{rx}.{rz}.mca → {len(entities)} Block Entities gefunden")

    print(f"\n✅ Gesamt: {len(all_entities)} Block Entities in {len(regions)} Region(en)")
    return all_entities