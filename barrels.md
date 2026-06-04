# Barrel Writer – Brief für Claude Code

## Kontext

Wir bauen einen Minecraft NBT Data Crawler in Python (offline).
Der Barrel Writer ist das letzte Modul – er nimmt Create Filter Items
und schreibt sie in vorplatzierte Barrels mit einem "FB"-Sign darüber.

---

## Projektstruktur

```
nbt_crawler/
├── main.py
├── world_picker.py       # Welt + Spieler auswählen, Logout-Pos lesen
├── chunk_scanner.py      # Region-Files im Radius scannen
├── entity_parser.py      # Items aus Block Entities extrahieren
├── item_report.py        # Report + User-Bestätigung
└── region_io.py          # Region lesen/schreiben (fertig, siehe unten)
```

---

## Learnings & Gotchas

### nbtlib
- Alle NBT-Tag-Typen haben `.value` um den Python-Typ zu bekommen
- `TAG_Double` erbt direkt von `float` → kein `.value` nötig
- `TAG_Int` braucht `.value` für Vergleiche und Zuweisungen
- Strings setzen: `nbtlib.String("minecraft:chest")`
- Chunk NBT lesen: `nbtlib.File.parse(io.BytesIO(raw_bytes))`
- Root-Tags sind direkt zugänglich: `nbt_data["block_entities"]`, NICHT `nbt_data[""]["block_entities"]`

### Region File Format (.mca)
- Header: 1024 x 4-byte Chunk-Location-Einträge
- Location Entry: `(offset << 8) | sector_count` (big-endian uint32)
- Offset in 4096-Byte Sektoren; `offset * 4096` = Byte-Position in der Datei
- Chunk-Daten: 4 bytes length + 1 byte compression type (2=zlib) + N bytes
- **KRITISCH:** Beim Zurückschreiben muss `len(compressed) <= (sector_count * 4096 - 5)`
  sonst überschreibt man den nächsten Chunk! Immer prüfen!
- Chunk-Header-Offset: `4 * ((cx % 32) + (cz % 32) * 32)`

### Blockstate vs Block Entity
- Minecraft braucht **beides** geändert:
  1. Block Entity `id` Tag in `nbt_data["block_entities"]`
  2. `Name` in der Blockstate-Palette: `nbt_data["sections"][i]["block_states"]["palette"]`
- Nur die Block Entity zu ändern reicht NICHT – Minecraft ignoriert es

### Signs (ab Minecraft 1.20)
```
front_text → messages → [0] = Zeile 1 als JSON String
z.B. '{"text":"FB"}'
```
Alle Sign-Typen akzeptieren: `"sign" in entity_id` (oak_sign, spruce_sign, etc.)

### anvil-parser2
- Nur zum **Lesen** geeignet (`Region.from_file`, `chunk.get_block`)
- **Kein Schreiben** möglich – `EmptyRegion` ist nur für neue Regions
- `chunk.data` ist ein `nbt.nbt.NBTFile` (andere Library!) – nicht mit nbtlib mischen
- Für alles Schreiben: direkt mit `region_io.py` arbeiten

---

## region_io.py (fertig, nicht ändern)

```python
def read_chunk_nbt(region_path: Path, cx: int, cz: int) -> nbtlib.File | None
def write_chunk_nbt(region_path: Path, cx: int, cz: int, nbt_data: nbtlib.File) -> bool
```

Koordinaten-Helpers (inline verwenden):
```python
cx, cz = bx >> 4, bz >> 4          # Block → Chunk
rx, rz = cx >> 5, cz >> 5          # Chunk → Region
region_path = world / "region" / f"r.{rx}.{rz}.mca"
```

---

## Barrel Writer – Aufgabe

### Input
- `all_entities`: Liste aller Block Entities im Radius (aus chunk_scanner)
- `parsed_entities`: Gefilterte Create Filter Entities (aus entity_parser),
  nur `is_quark_chest == False`
- `player_x, player_z`: Logout-Position des Spielers
- `world_path: Path`

### Schritt 1 – FB-Barrels finden

Suche in `all_entities` nach:
1. `minecraft:barrel` Block Entities
2. `*sign*` Block Entities bei `y+1` mit `front_text.messages[0]` == `'{"text":"FB"}'`

```python
def find_fb_barrels(all_entities, player_x, player_z) -> list[dict]:
    # Gibt Liste von {x, y, z} zurück, sortiert nach Distanz zu player_x/z
    # Sortierung: euklidische 2D-Distanz (y ignorieren)
```

### Schritt 2 – Items in Barrels schreiben

```python
def fill_barrels(world_path, fb_barrels, parsed_entities) -> None:
```

- Alle Items aus `parsed_entities` (nur `is_quark_chest == False`) in einen Pool sammeln
- Items nacheinander in das nächste Barrel schreiben (nächstes = erstes in der
  nach Distanz sortierten Liste)
- Ein Barrel hat **27 Slots** (Index 0–26)
- Bei Überlauf: nächstes freies Barrel nehmen
- Barrel NBT Struktur schreiben:

```
block_entities eintrag für das Barrel:
  id: "minecraft:barrel"
  x, y, z: Position
  Items: TAG_List von TAG_Compound mit:
    - id: TAG_String  (z.B. "minecraft:iron_ingot")
    - count: TAG_Byte (Anzahl, meist 1 für Filter-Items)
    - Slot: TAG_Byte  (0–26)
```

nbtlib Beispiel für ein Item:
```python
nbtlib.Compound({
    "id": nbtlib.String("minecraft:iron_ingot"),
    "count": nbtlib.Byte(1),
    "Slot": nbtlib.Byte(slot_index),
})
```

### Schritt 3 – Barrel Block Entity in Region schreiben

Wie bei `convert_quark_chest`:
1. `read_chunk_nbt` aufrufen
2. In `nbt_data["block_entities"]` den Barrel-Eintrag anhand x/y/z finden
3. `Items` Tag ersetzen/setzen
4. `write_chunk_nbt` aufrufen
5. **Immer prüfen** ob `write_chunk_nbt` True zurückgibt!

### Wichtige Checks beim Entwickeln

Nach jedem `write_chunk_nbt`:
```python
# Verify lesen
verify = read_chunk_nbt(region_path, cx, cz)
for be in verify["block_entities"]:
    if be["x"] == bx and be["y"] == by and be["z"] == bz:
        print(f"Items im Barrel: {len(be.get('Items', []))}")
```

Erst wenn Verify korrekt ist → nächsten Schritt angehen.
Nicht alles auf einmal bauen – Schritt für Schritt testen!

---

## Workflow für Claude Code

1. `find_fb_barrels` implementieren und testen (einfach alle gefundenen Barrels ausgeben)
2. Einen einzelnen Barrel mit einem Item befüllen und verifizieren
3. Erst dann den vollen `fill_barrels` mit Pool + Überlauf bauen
4. Am Ende: debug prints raus, saubere Fehlerbehandlung rein