import json, time
from pathlib import Path

CACHE_PATH = Path.home() / ".ayga_cli" / "sources_cache.json"
CACHE_TTL = 300  # 5 minutes

def load_cache() -> list[dict] | None:
    """Load sources from cache if fresh. Returns None if missing or expired."""
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text())
        if time.time() - data.get("ts", 0) > CACHE_TTL:
            return None
        return data.get("sources", [])
    except Exception:
        return None

def save_cache(sources: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"ts": time.time(), "sources": sources}))

def clear_cache() -> None:
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
