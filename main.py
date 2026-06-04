from collections import defaultdict

import nbtlib
from nbt.nbt import TAG_Byte
from nbtlib import nbt

from block_entities import parse_entities
from config import get_minecraft_path
from players import load_usercache, list_players, get_player_position
from region_io import convert_all_quark_chests
from regions import scan_world_radius
from saves import get_saves, get_saves_path


def print_item_report(parsed_entities: list[dict]) -> bool:
    """
    Zeigt gefundene Items gruppiert nach Container-Typ.
    Gibt True zurück, wenn der User bestätigt, und False, wenn abgebrochen.
    """

    quark_chests = [e for e in parsed_entities if e["is_quark_chest"]]
    create_filters = [e for e in parsed_entities if not e["is_quark_chest"]]

    # Gesamtübersicht: alle Items zusammengezählt
    total_items: dict[str, int] = defaultdict(int)
    for entity in parsed_entities:
        for item in entity["items"]:
            val = item.get("count")
            if val is None:
                val = 1
            elif not isinstance(val, int):
                val = int(val.value)

            # Debug Print val Type
            total_items[item["id"]] += val

    print("\n" + "=" * 50)
    print(f"📦 ITEM REPORT")
    print("=" * 50)

    print(f"\n🗃️  Quark Chests gefunden: {len(quark_chests)}")
    for e in quark_chests:
        print(f"  @ X={e['x']} Y={e['y']} Z={e['z']}")
        for item in e["items"]:
            print(f"      Slot {item['slot']:2d}: {item['id']} x{item.get('count', '?')}")

    print(f"\n⚙️  Create Filter gefunden: {len(create_filters)}")
    for e in create_filters:
        print(f"  [{e['id']}] @ X={e['x']} Y={e['y']} Z={e['z']}")
        for item in e["items"]:
            print(f"      {item['id']} x{item.get('count', '?')}")

    print(f"\n📊 Alle Items zusammengefasst:")
    for item_id, count in sorted(total_items.items()):
        print(f"  {item_id:<50} x{count}")

    print("\n" + "=" * 50)
    print("✅ Folgendes wird gemacht:")
    print(" - 3 Quark Chests → Vanilla Chests konvertieren")
    print(" - 12 Filter-Items → in FB-Barrels schreiben)")
    confirm = input("Fortfahren? (j/n):").strip().lower()
    return confirm == "j"


def main():
    try:
        mc_path = get_minecraft_path()

        # 1. Welt auswählen
        print("1. Welt auswählen:")
        worlds = get_saves(get_saves_path(mc_path))
        for i, (name, path) in enumerate(worlds):
            print(f"  [{i}] {name}  ({path.name})")
        selected_world = worlds[int(input("\nWelt: "))][1]
        print(f"  → {selected_world.name}")

        # 2. Spieler auswählen
        print("\n2. Spieler auswählen:")
        usercache = load_usercache(mc_path)
        players = list_players(selected_world, usercache)
        for i, (name, uuid, _) in enumerate(players):
            print(f"  [{i}] {name} ({uuid})")
        selected_name, _, selected_dat = players[int(input("\nSpieler: "))]
        x, y, z = get_player_position(selected_dat)
        print(f"  → Logout-Position: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")

        # 3. Scannen
        radius = int(input("\nRadius in Chunks (default 20): ") or "20")
        print(f"\n🔍 Scanne {radius} Chunks um {selected_name}s Position...")
        all_entities = scan_world_radius(selected_world, x, z, radius)

        # 4. Parsen
        parsed = parse_entities(all_entities)
        if not parsed:
            print("❌ Keine relevanten Container gefunden!")
            return

        # 5. Report + Bestätigung
        if not print_item_report(parsed):
            print("❌ Abgebrochen.")
            return

        # 6. Quark Chests konvertieren
        convert_all_quark_chests(selected_world, parsed)

        # 7. Create Filter → Barrels (kommt noch)
        print("\n🔨 Barrel-Writer kommt noch...")

    except Exception as e:
        print(f"❌ Fehler: {e}")
        raise


if __name__ == "__main__":
    main()
