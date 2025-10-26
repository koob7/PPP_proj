# -------------------------
# Cache helpers
# -------------------------

import pickle
import hashlib
from typing import List, Optional, Tuple
from pathlib import Path

from logger import logger

class CacheHelper:
    DEFAULT_CACHE_DIR = Path(".cache")

    @staticmethod
    def get_cache_key(filenames: List[Path]) -> str:
        """Generuje hash na podstawie ścieżek plików + mtime (jeśli plik istnieje)."""
        h = hashlib.md5()
        for p in filenames:
            if p.exists():
                mtime = p.stat().st_mtime
                h.update(f"{str(p.resolve())}:{mtime}".encode())
            else:
                h.update(f"{str(p.resolve())}:missing".encode())
        return h.hexdigest()

    @staticmethod
    def get_cache_path(filenames: List[Path], cache_dir: Optional[Path] = DEFAULT_CACHE_DIR) -> Path:
        """Zwraca pełną ścieżkę do pliku cache."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        name = f"shapes_cache_{CacheHelper.get_cache_key(filenames)}.pkl"
        return cache_dir / name

    @staticmethod
    def load_cache(filenames: List[Path], cache_dir: Optional[Path] = DEFAULT_CACHE_DIR) -> Optional[Tuple[List, List]]:
        """Ładuje dane z cache, jeśli istnieje."""
        cache_path = CacheHelper.get_cache_path(filenames, cache_dir)
        if not cache_path.exists():
            logger.info("Brak cache (%s).", cache_path)
            return None
        try:
            logger.info("Ładowanie cache: %s", cache_path)
            with cache_path.open("rb") as f:
                data = pickle.load(f)
            return data.get("shapes"), data.get("statuses")
        except Exception as e:
            logger.warning("Błąd odczytu cache: %s — będzie wczytane z plików STEP.", e)
            return None

    @staticmethod
    def save_cache(filenames: List[Path], shapes: List, statuses: List, cache_dir: Optional[Path] = DEFAULT_CACHE_DIR) -> None:
        """Zapisuje dane do cache."""
        cache_path = CacheHelper.get_cache_path(filenames, cache_dir)
        try:
            with cache_path.open("wb") as f:
                pickle.dump({"shapes": shapes, "statuses": statuses}, f)
            logger.info("Zapisano cache: %s", cache_path)
        except Exception as e:
            logger.warning("Nie udało się zapisać cache: %s", e)