import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

@lru_cache(maxsize=None)
def load(name: str) -> list[dict]:
    return json.loads((_DATA_DIR / f"{name}.json").read_text())
