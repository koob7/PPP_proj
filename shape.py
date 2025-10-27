from pathlib import Path
from typing import List, Optional, Tuple

from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone

from logger import logger
from cache import CacheHelper
from geometry_helper import simplify_shapes, center_shapes

class StepLoader:
    def __init__(self, filenames: List[Path], cache_dir: Optional[Path] = None):
        self.filenames = filenames
        self.cache_dir = cache_dir
        self.raw_shapes: Optional[List] = None
        self.simplified_shapes: Optional[List] = None
        self.shapes: Optional[List] = None
        self.statuses: List = []

    def read_step_files(self) -> Tuple[Optional[List], List]:
        """Wczytaj pliki STEP z podfolderu 'shapes' (jeśli potrzeba) i zwróć (shapes, statuses)."""
        readers = []
        statuses = []
        shapes_dir = Path("shapes")
        for p in self.filenames:
            # Jeśli ścieżka nie istnieje, spróbuj w podfolderze 'shapes'
            candidate = p
            if not candidate.exists():
                candidate = shapes_dir / p

            rdr = STEPControl_Reader()
            status = rdr.ReadFile(str(candidate))
            readers.append(rdr)
            statuses.append(status)

        if not all(s == IFSelect_RetDone for s in statuses):
            logger.error("Jednen z plików nie został poprawnie wczytany: %s", statuses)
            return None, statuses

        shapes = []
        for rdr in readers:
            rdr.TransferRoots()
            shapes.append(rdr.Shape())
        return shapes, statuses

    def load_shapes(self) -> Optional[List]:
        """
        Ładuje kształty: najpierw próbuje z cache, jeśli brak -> wczytuje z plików i zapisuje cache.
        Zwraca listę kształtów (List) albo None przy błędzie.
        """
        cached = CacheHelper.load_cache(self.filenames, self.cache_dir)
        if cached:
            shapes, statuses = cached
            self.shapes = shapes
            self.statuses = statuses
            logger.info("Załadowano shapes z cache.")
        else:
            shapes, statuses = self.read_step_files()
            if shapes is None:
                logger.error("Nie udało się wczytać plików STEP.")
                return None
            self.raw_shapes = shapes
            self.statuses = statuses
            # Placeholder: tutaj możesz wstawić uproszczenie i centrowanie
            self.simplified_shapes = simplify_shapes(self.raw_shapes)
            self.shapes = center_shapes(self.simplified_shapes)
            # zapis cache
            CacheHelper.save_cache(self.filenames, self.shapes, statuses, self.cache_dir)
        return self.shapes
