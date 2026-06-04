from pathlib import Path

import anvil
import nbtlib

DIRECT_ITEMS_IDS = {
    "quark:variant_chest",
    "quark:trapped_chest",
}

CREATE_FILTER_IDS = {
}

FILTER_COMPOUND_IDS = {
    "create:brass_tunnel"
    "create:funnel",
    "create:basin",
    "create:depot",
    "create:stockpile_switch",
    "create:item_hatch",
    "create:deployer"
}

INVENTORY_COMPOUND_IDS = {
    "create:item_vault",
}

RELEVANT_IDS = DIRECT_ITEMS_IDS | FILTER_COMPOUND_IDS | INVENTORY_COMPOUND_IDS


def parse_direct_items(be_nbt: dict) -> list[dict]:
    """Extrahiert Items aus dem Items-Tag einer Block Entity"""
    items = []

    for item in be_nbt.get("Items", []):
        items.append({
            "id": item["id"].value,
            "count": item["Count"].value,
            "slot": item["Slot"].value,
        })

    return items


def parse_filter_item(be_nbt: dict) -> list[dict]:
    """Für Blocks mit einem einzelnen Filter-Compound (funnel, hatch, etc.)"""
    filter_tag = be_nbt.get("Filter")
    if not filter_tag or "id" not in filter_tag:
        return []

    item_id = filter_tag["id"].value
    if item_id == "minecraft:air":
        return []

    return [{
        "id": filter_tag["id"].value,
        "count": filter_tag.get("count", 1),  # Filter hat oft keine Count
        "slot": 0,
    }]


def parse_held_item(be_nbt: dict) -> list[dict]:
    """Für Deployer HeldItem"""
    held = be_nbt.get("HeldItem")
    if not held or "id" not in held:
        return []

    item_id = held["id"].value
    if item_id == "minecraft:air":
        return []

    return [{
        "id": held["id"].value,
        "count": held.get("Count", 1),
        "slot": 0,
    }]


def parse_inventory_compound(be_nbt: dict) -> list[dict]:
    """Für Blocks mit verschachteltem Inventory Compound (item_vault)"""
    inventory = be_nbt.get("Inventory")
    if not inventory or "Items" not in inventory:
        return []

    items = []
    for item in inventory["Items"]:
        items.append({
            "id": item["id"].value,
            "count": item["Count"].value,
            "slot": item["Slot"].value,
        })
    return items

def parse_entities(all_entities: list[dict]) -> list[dict]:
    result = []

    for entity in all_entities:
        eid = entity["id"]
        nbt = entity["nbt"]

        if eid not in RELEVANT_IDS:
            continue

        if eid in DIRECT_ITEMS_IDS:
            items = parse_direct_items(nbt)
        elif eid in FILTER_COMPOUND_IDS:
            items = parse_filter_item(nbt)

            if eid == "create:deployer":
                held_items = parse_held_item(nbt)
                items += held_items

            seen_ids = set()
            deduped_items = []
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    deduped_items.append(item)
            items = deduped_items

        elif eid in INVENTORY_COMPOUND_IDS:
            items = parse_inventory_compound(nbt)
        else:
            continue

        if not items:
            continue

        result.append({
            "id": eid,
            "x": entity["x"],
            "y": entity["y"],
            "z": entity["z"],
            "items": items,
            "is_quark_chest": eid in DIRECT_ITEMS_IDS,
        })

    return result

#
# Quark Chests
#


def convert_quark_chests(
        parsed_entities: list[dict],
        world_path: Path,
):
    quark_chests = [e for e in parsed_entities if e["is_quark_chest"]]

    if not quark_chests:
        print("Keine Quark Chests gefunden!")
        return

    # Gruppieren nach Region File
    from collections import defaultdict
    by_region: dict[tuple, list] = defaultdict(list)
    for chest in quark_chests:
        rx = chest["x"] >> 9  # = chunk_x >> 5 = block_x >> 9
        rz = chest["z"] >> 9
        by_region[(rx, rz)].append(chest)

    region_dir = world_path / "region"

    for (rx, rz), chests in by_region.items():
        region_path = region_dir / f"r.{rx}.{rz}.mca"
        if not region_path.exists():
            print(f"⚠️  Region {region_path.name} nicht gefunden!")
            continue

        region = anvil.Region.from_file(str(region_path))

        for chest in chests:
            cx = chest["x"] >> 4
            cz = chest["z"] >> 4
            local_cx = cx % 32
            local_cz = cz % 32

            chunk = region.get_chunk(local_cx, local_cz)
            block_entities = chunk.data["block_entities"]

            for be in block_entities:
                if (be["x"].value == chest["x"] and
                        be["y"].value == chest["y"] and
                        be["z"].value == chest["z"]):
                    be["id"] = nbtlib.String("minecraft:chest")
                    print(f"  ✅ Konvertiert @ X={chest['x']} Y={chest['y']} Z={chest['z']}")
                    break

        # Region zurückschreiben
        # anvil-parser2 kann einzelne Chunks zurückschreiben?


#
# Barrels
#

import json

def find_fb_barrels(all_entities: list[dict], player_x: float, player_z: float) -> list[dict]:
    """
    Findet alle minecraft:barrel Block Entities die ein FB-Sign direkt darüber haben.
    Sortiert nach Distanz zur Logout-Position.
    """

    # Signs und Barrels separat sammeln
    signs = {}   # (x, y, z) → nbt
    barrels = [] # list of {x, y, z}

    for entity in all_entities:
        eid = entity["id"]
        x, y, z = entity["x"], entity["y"], entity["z"]

        if eid == "minecraft:barrel":
            barrels.append({"x": x, "y": y, "z": z})

        elif "sign" in eid:  # oak_sign, spruce_sign, etc.
            try:
                front = entity["nbt"]["front_text"]
                messages = front["messages"]
                line1 = json.loads(str(messages[0]))
                if line1.get("text", "").strip() == "FB":
                    signs[(x, y, z)] = entity["nbt"]
            except Exception:
                continue

    # Barrels mit FB-Sign direkt darüber filtern
    fb_barrels = []
    for barrel in barrels:
        sign_pos = (barrel["x"], barrel["y"] + 1, barrel["z"])
        if sign_pos in signs:
            fb_barrels.append(barrel)

    # Nach Distanz zur Logout-Position sortieren (cbrt dist)
    fb_barrels.sort(key=lambda b: (
        (b["x"] - player_x) ** 2 + (b["z"] - player_z) ** 2
    ) ** 0.5)

    print(f"🛢️  {len(fb_barrels)} FB-Barrels gefunden!")
    return fb_barrels