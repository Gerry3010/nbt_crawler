from pathlib import Path

import nbtlib


def get_saves_path(mc_path: Path) -> Path:
    return mc_path / "saves"


def get_saves(saves_path: Path) -> list[tuple[str, Path]]:
    if not saves_path.exists():
        raise FileNotFoundError(f"Minecraft directory not found at {saves_path}")

    worlds = []
    for folder in sorted(saves_path.iterdir()):
        if folder.is_dir() and (folder / "level.dat").exists():
            name = get_world_name(folder)
            worlds.append((name, folder))
    return worlds


def get_world_name(world_path: Path) -> str:
    level_dat = nbtlib.load(world_path / "level.dat")
    return str(level_dat["Data"]["LevelName"])
