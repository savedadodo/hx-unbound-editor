"""Optional display names for stock models, from a CSV the user keeps locally (never part of this package).

For firmware whose model list was renamed on the device, the editor can show the same names. The file
maps HX Edit's symbolic IDs to the names to show:

    internal,floor_name,real_name
    HD2_DistMinotaurMono,Minotaur,Klon Centaur

Columns `internal` (or `symbol`) and `real_name` (or `name`); others are ignored. Location: the
HX_UNBOUND_NAMES environment variable, else custom-names.csv in this folder (ignored by git). Display
only: the device, presets, model numbers and the server's own state are unchanged; renamed rows keep
the HX Edit name in `stockName`."""
import copy
import csv
from functools import lru_cache
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAM = 380


def names_path():
    return Path(os.environ.get("HX_UNBOUND_NAMES") or ROOT / "custom-names.csv")


@lru_cache(maxsize=4)
def _load(path, modified):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    names = {}
    for row in rows:
        symbol = (row.get("internal") or row.get("symbol") or "").strip()
        name = (row.get("real_name") or row.get("name") or "").strip()
        if symbol and name:
            names[symbol] = name
    return names


def symbol_names():
    """{symbol: name} from the user's file, {} when there is none or it can't be read."""
    path = names_path()
    try:
        return _load(str(path), path.stat().st_mtime_ns)
    except (OSError, UnicodeError, csv.Error):
        return {}


def model_names(placements):
    """{model number: name} through the bridge's stock list (number -> symbol)."""
    names = symbol_names()
    if not names or not placements:
        return {}
    return {row["model"]: names[row["symbol"]] for row in json.loads(placements)
            if isinstance(row, dict) and row.get("symbol") in names and row.get("model") != NAM}


def _rename(row, by_model):
    name = by_model.get(row.get("model"))
    if name and row.get("model") != NAM:
        row.setdefault("stockName", row.get("name"))
        row["name"] = name


def catalog(placements):
    """The bridge's stock list (bytes) with the custom names."""
    by_model = model_names(placements)
    if not by_model:
        return placements
    rows = json.loads(placements)
    for row in rows:
        _rename(row, by_model)
    return json.dumps(rows).encode()


def visual(metadata, placements):
    """The model browser's metadata (bytes) with the custom names."""
    by_model = model_names(placements)
    if not by_model:
        return metadata
    data = json.loads(metadata)
    for row in data.get("models", []):
        _rename(row, by_model)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def state(snapshot, placements):
    """A copy of the live state for the page, its stock blocks renamed (NAM blocks keep capture names)."""
    board = snapshot.get("board")
    by_model = model_names(placements) if board else {}
    if not by_model:
        return snapshot
    board = copy.deepcopy(board)
    for block in board.get("blocks", []):
        _rename(block, by_model)
    return {**snapshot, "board": board}
