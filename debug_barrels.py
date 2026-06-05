"""
Diagnose-Script für den Barrel-Writer.
Führe aus bevor du fill_barrels aufrufst, um zu sehen was gefunden wird.
"""
import json
from pathlib import Path

import nbtlib

from config import get_minecraft_path
from players import load_usercache, list_players, get_player_position
from region_io import read_chunk_nbt
from regions import scan_world_radius
from saves import get_saves, get_saves_path


def diagnose(world_path: Path, all_entities: list[dict], player_x: float, player_z: float):
    print("\n" + "=" * 60)
    print("DIAGNOSE: Barrels & Signs")
    print("=" * 60)

    # 1. Alle Barrels
    barrels = [e for e in all_entities if e["id"] == "minecraft:barrel"]
    print(f"\n[1] minecraft:barrel gefunden: {len(barrels)}")
    for b in barrels:
        print(f"    @ X={b['x']} Y={b['y']} Z={b['z']}")

    # 2. Alle Signs — zeige rohen Text
    sign_entities = [e for e in all_entities if "sign" in e["id"]]
    print(f"\n[2] Signs gefunden: {len(sign_entities)}")
    for s in sign_entities:
        x, y, z = s["x"], s["y"], s["z"]
        nbt = s["nbt"]
        try:
            front = nbt["front_text"]
            msgs = front["messages"]
            raw = [str(m) for m in msgs]
            print(f"    [{s['id']}] @ X={x} Y={y} Z={z}")
            print(f"      Zeilen (roh): {raw}")
        except Exception as e:
            print(f"    [{s['id']}] @ X={x} Y={y} Z={z}  ← FEHLER: {e}")

    # 3. FB-Sign Matches
    print("\n[3] FB-Sign Matching (Sign direkt über Barrel):")
    fb_barrels = []
    for barrel in barrels:
        bx, by, bz = barrel["x"], barrel["y"], barrel["z"]
        sign_pos_above = (bx, by + 1, bz)
        matched_sign = None
        for s in sign_entities:
            if (s["x"], s["y"], s["z"]) == sign_pos_above:
                matched_sign = s
                break
        if matched_sign:
            # Prüfe ob Text "FB"
            try:
                msgs = matched_sign["nbt"]["front_text"]["messages"]
                line1 = json.loads(str(msgs[0]))
                text = line1.get("text", "").strip()
                is_fb = text == "FB"
                print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← Sign text='{text}'  FB={is_fb}")
                if is_fb:
                    fb_barrels.append(barrel)
            except Exception as e:
                print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← Sign Parse-Fehler: {e}")
        else:
            print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← kein Sign direkt darüber")

    print(f"\n  → {len(fb_barrels)} FB-Barrel(s) gefunden")

    # 4. Für jeden FB-Barrel: NBT direkt aus Region lesen
    print("\n[4] NBT-Check der FB-Barrels:")
    for barrel in fb_barrels:
        bx, by, bz = barrel["x"], barrel["y"], barrel["z"]
        cx, cz = bx >> 4, bz >> 4
        rx, rz = cx >> 5, cz >> 5
        region_path = world_path / "region" / f"r.{rx}.{rz}.mca"

        nbt_data = read_chunk_nbt(region_path, cx, cz)
        if nbt_data is None:
            print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← Chunk nicht lesbar!")
            continue

        found = False
        for be in nbt_data["block_entities"]:
            if be["x"] == bx and be["y"] == by and be["z"] == bz:
                found = True
                items = be.get("Items", [])
                print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← BE gefunden, {len(items)} Item(s)")
                if items:
                    print(f"      Erstes Item Keys: {list(items[0].keys())}")
                    print(f"      Erstes Item: {dict(items[0])}")
                break

        if not found:
            all_bes = [(be["x"], be["y"], be["z"]) for be in nbt_data["block_entities"]]
            print(f"    Barrel @ X={bx} Y={by} Z={bz}  ← BE NICHT GEFUNDEN im Chunk!")
            print(f"      Vorhandene BEs im Chunk: {all_bes}")

    print("\n" + "=" * 60)


def main():
    mc_path = get_minecraft_path()

    print("Welt auswählen:")
    worlds = get_saves(get_saves_path(mc_path))
    for i, (name, path) in enumerate(worlds):
        print(f"  [{i}] {name}")
    selected_world = worlds[int(input("Welt: "))][1]

    print("\nSpieler auswählen:")
    usercache = load_usercache(mc_path)
    players = list_players(selected_world, usercache)
    for i, (name, uuid, _) in enumerate(players):
        print(f"  [{i}] {name}")
    _, _, selected_dat = players[int(input("Spieler: "))]
    x, y, z = get_player_position(selected_dat)
    print(f"Logout-Position: X={x:.1f} Y={y:.1f} Z={z:.1f}")

    radius = int(input("\nRadius in Chunks (default 20): ") or "20")
    print(f"\nScanne {radius} Chunks...")
    all_entities = scan_world_radius(selected_world, x, z, radius)

    diagnose(selected_world, all_entities, x, z)


if __name__ == "__main__":
    main()
