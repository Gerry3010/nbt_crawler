# Minecraft NBT Crawler

Dieses Tool hilft dabei, bestimmte Block-Entities in Minecraft-Welt-Dateien zu finden und zu manipulieren. Es wurde speziell entwickelt, um Container-Inhalte zu analysieren und Konvertierungen vorzunehmen.

## Features

- **Quark Chest Konvertierung**: Findet `quark:variant_chest` und `quark:trapped_chest` und bereitet sie für die Konvertierung in Vanilla-Truhen vor.
- **Create Mod Support**: Erkennt Filter und Inventare aus dem Create-Mod (z. B. Funnels, Basins, Item Vaults).
- **Automatisches Befüllen**: Schreibt gefundene Filter-Items direkt in Functional Storage Barrels (`fb-barrels`).
- **Radius-Scan**: Scant die Welt in einem konfigurierbaren Radius um die letzte Position eines Spielers.

## Installation

1. Klone das Repository:
   ```bash
   git clone <repository-url>
   cd nbt_crawler
   ```

2. Erstelle eine virtuelle Umgebung und installiere die Abhängigkeiten:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unter Windows: .venv\Scripts\activate
   pip install nbtlib anvil-parser nbt
   ```

## Benutzung

Starte das Hauptskript:
```bash
python main.py
```

Das Skript wird dich durch folgende Schritte führen:
1. Auswahl der Minecraft-Welt (erkennt automatisch den `.minecraft`-Ordner).
2. Auswahl des Spielers (um die Scan-Position festzulegen).
3. Eingabe des Scan-Radius (in Chunks).
4. Anzeige eines Reports der gefundenen Items.
5. Bestätigung der Änderungen.

## Projektstruktur

- `main.py`: Haupteinstiegspunkt und User-Interaktion.
- `block_entities.py`: Logik zum Parsen verschiedener Minecraft-Block-NBT-Daten.
- `region_io.py`: Handling von Region-Dateien (`.mca`).
- `barrel_writer.py`: Spezielle Logik für Functional Storage Barrels.
- `saves.py` & `config.py`: Hilfsfunktionen für Welt-Auswahl und Pfade.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

## Hinweis
**Wichtig:** Erstelle immer ein Backup deiner Welt, bevor du dieses Tool benutzt! Die direkte Manipulation von NBT-Daten kann bei Fehlern zu Welt-Korruption führen.
