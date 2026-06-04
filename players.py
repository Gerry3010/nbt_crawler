from pathlib import Path

import nbtlib


def load_usercache(minecraft_path: Path) -> dict[str, str]:
    """Gibt {uuid: name} zurück"""
    cache_file = minecraft_path / "usercache.json"
    if not cache_file.exists():
        return {}

    import json
    with open(cache_file, "r") as f:
        data = json.load(f)

    return {entry["uuid"]: entry["name"] for entry in data}

def list_players(world_path: Path, usercache: dict[str, str]) -> list[tuple[str, str, Path]]:
    """Gibt eine Liste von (anzeigename, uuid, dat_path) zurück"""
    playerdata_path = world_path / "playerdata"
    players = []

    for dat_file in sorted(playerdata_path.glob("*.dat")):
        uuid = dat_file.stem  # Dateiname ohne .dat = UUID
        name = usercache.get(uuid, f"<Unbekannt: {uuid}>")
        players.append((name, uuid, dat_file))

    return players

def get_player_position(dat_path: Path) -> tuple[float, float, float]:
    data = nbtlib.load(dat_path)
    pos = data["Pos"]  # List von 3 Doubles
    return float(pos[0]), float(pos[1]), float(pos[2])