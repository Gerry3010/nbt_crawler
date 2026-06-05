import json
from pathlib import Path

import nbtlib

from region_io import read_chunk_nbt, write_chunk_nbt


def find_fb_barrels(all_entities: list[dict], player_x: float, player_z: float) -> list[dict]:
    """
    Findet alle minecraft:barrel Block Entities die ein FB-Sign direkt darüber haben.
    Sortiert nach euklidischer 2D-Distanz zur Logout-Position.
    """
    signs = {}
    barrels = []

    for entity in all_entities:
        eid = entity["id"]
        x, y, z = entity["x"], entity["y"], entity["z"]

        if eid == "minecraft:barrel":
            barrels.append({"x": x, "y": y, "z": z})
        elif "sign" in eid:
            try:
                front = entity["nbt"]["front_text"]
                messages = front["messages"]
                line1 = json.loads(str(messages[0]))
                if line1.get("text", "").strip() == "FB":
                    signs[(x, y, z)] = entity["nbt"]
            except Exception:
                continue

    fb_barrels = []
    for barrel in barrels:
        sign_pos = (barrel["x"], barrel["y"] + 1, barrel["z"])
        if sign_pos in signs:
            fb_barrels.append(barrel)

    fb_barrels.sort(key=lambda b: (
        (b["x"] - player_x) ** 2 + (b["z"] - player_z) ** 2
    ) ** 0.5)

    print(f"🛢️  {len(fb_barrels)} FB-Barrel(s) gefunden!")
    return fb_barrels


def fill_barrels(world_path: Path, fb_barrels: list[dict], parsed_entities: list[dict]) -> None:
    """
    Schreibt create:filter Items komplett (inklusive tag-Compound) in die FB-Barrels.
    Das Filter-Compound wird per nbtlib direkt aus der Quell-Entity gelesen,
    damit das verschachtelte Items-Tag erhalten bleibt.
    """
    # Quellen: Entities die ein create:filter Item enthalten
    filter_sources = [
        {"entity_x": e["x"], "entity_y": e["y"], "entity_z": e["z"],
         "source_field": item.get("source_field", "Filter")}
        for e in parsed_entities
        if not e["is_quark_chest"]
        for item in e["items"]
        if item["id"] == "create:filter"
    ]

    # Alter Item-Pool (alle Items, unkomplett ohne tag):
    # item_pool = [
    #     item
    #     for entity in parsed_entities
    #     if not entity["is_quark_chest"]
    #     for item in entity["items"]
    # ]

    if not filter_sources:
        print("Keine create:filter Items gefunden.")
        return

    if not fb_barrels:
        print("⚠️  Keine FB-Barrels gefunden!")
        return

    print(f"📦 {len(filter_sources)} create:filter(s) → {len(fb_barrels)} FB-Barrel(s) schreiben...")

    source_idx = 0

    for barrel in fb_barrels:
        if source_idx >= len(filter_sources):
            break

        bx, by, bz = barrel["x"], barrel["y"], barrel["z"]
        cx, cz = bx >> 4, bz >> 4
        rx, rz = cx >> 5, cz >> 5
        barrel_region = world_path / "region" / f"r.{rx}.{rz}.mca"

        barrel_nbt = read_chunk_nbt(barrel_region, cx, cz)
        if barrel_nbt is None:
            print(f"  ⚠️  Chunk nicht gefunden für Barrel @ X={bx} Y={by} Z={bz}")
            continue

        source_idx_checkpoint = source_idx  # bei Write-Fehler wiederherstellen

        items_nbt = nbtlib.List[nbtlib.Compound]()
        slot = 0

        while source_idx < len(filter_sources) and slot < 27:
            src = filter_sources[source_idx]
            sx, sy, sz = src["entity_x"], src["entity_y"], src["entity_z"]
            scx, scz = sx >> 4, sz >> 4
            srx, srz = scx >> 5, scz >> 5
            src_region = world_path / "region" / f"r.{srx}.{srz}.mca"

            # Quell-Entity per nbtlib lesen → Filter-Compound ist bereits nbtlib-Typ
            src_nbt = read_chunk_nbt(src_region, scx, scz)
            if src_nbt is None:
                source_idx += 1
                continue

            filter_nbt = None
            for be in src_nbt["block_entities"]:
                if be["x"] == sx and be["y"] == sy and be["z"] == sz:
                    f = be.get(src["source_field"])
                    if f is not None and f.get("id") == "create:filter":
                        filter_nbt = f
                    break

            if filter_nbt is None:
                print(f"  ⚠️  create:filter nicht gefunden @ X={sx} Y={sy} Z={sz}")
                source_idx += 1
                continue

            # Komplettes Filter-Item in den Barrel-Slot schreiben
            item_data = {
                "id": nbtlib.String("create:filter"),
                "Count": nbtlib.Byte(1),
                "Slot": nbtlib.Byte(slot),
            }
            if "tag" in filter_nbt:
                item_data["tag"] = filter_nbt["tag"]

            # Alter Weg (ohne tag):
            # item_data = {
            #     "id": nbtlib.String(item["id"]),
            #     "Count": nbtlib.Byte(1),
            #     "Slot": nbtlib.Byte(slot),
            # }

            items_nbt.append(nbtlib.Compound(item_data))
            slot += 1
            source_idx += 1

        # Barrel Block Entity finden und Items setzen
        found = False
        for be in barrel_nbt["block_entities"]:
            if be["x"] == bx and be["y"] == by and be["z"] == bz:
                be["Items"] = items_nbt
                found = True
                break

        if not found:
            print(f"  ⚠️  Barrel Block Entity nicht gefunden @ X={bx} Y={by} Z={bz}")
            continue

        if not write_chunk_nbt(barrel_region, cx, cz, barrel_nbt):
            print(f"  ❌ Chunk zu voll @ X={bx} Y={by} Z={bz} → {slot} Filter gehen zum nächsten Barrel")
            source_idx = source_idx_checkpoint
            continue

        # Verify
        verify = read_chunk_nbt(barrel_region, cx, cz)
        verified_count = 0
        for be in verify["block_entities"]:
            if be["x"] == bx and be["y"] == by and be["z"] == bz:
                verified_count = len(be.get("Items", []))
                break

        print(f"  ✅ Barrel @ X={bx} Y={by} Z={bz} → {verified_count} Filter(s) geschrieben")

    if source_idx < len(filter_sources):
        remaining = len(filter_sources) - source_idx
        print(f"\n⚠️  {remaining} Filter nicht geschrieben – zu wenig freie FB-Barrels!")
    else:
        print(f"\n✅ Alle {len(filter_sources)} create:filter(s) in Barrels geschrieben.")
