#!/usr/bin/env python3
# coding: utf-8
"""
Refaktoryzowany viewer STEP (PyQt5 + pythonOCC).
- Klasa StepViewer enkapsuluje logikę aplikacji.
- Cache plików STEP w katalogu .cache (nazwa oparta na hash'ach nazw i mtime).
- Metody: load (automatycznie korzysta z cache jeśli dostępne), simplify, center, apply transforms, redraw.
"""

from __future__ import annotations
import logging
import os
import pickle
import hashlib
import math
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

# pythonOCC / OCC imports
from OCC.Display.backend import load_backend
load_backend("pyqt5")

from OCC.Display.qtDisplay import qtViewer3d
from OCC.Display.OCCViewer import rgb_color
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh

# PyQt5
from PyQt5.QtWidgets import QApplication, QSlider, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

# Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


TransformType = Dict[str, Any]  # {'translate': (x,y,z), 'rotations': [{'axis': (x,y,z), 'angle_deg': float}, ...]}


class StepViewer:
    def __init__(
        self,
        filenames: List[str],
        cache_dir: str = ".cache",
        marker_radius: float = 10.0,
    ):
        self.filenames = [Path(f) for f in filenames]
        self.cache_dir = Path(cache_dir)
        self.marker_radius = marker_radius

        # scene state
        self.shapes: Optional[List] = None           # shapes centered & simplified (used for display)
        self.raw_shapes: Optional[List] = None       # shapes as wczytane
        self.statuses: Optional[List] = None
        self.displayed_shapes: Optional[List] = None
        self.transforms_table: List[TransformType] = []
        self.shape_colors: List = []
        self.draw_table: List[bool] = []

        # PyQt / OCC display
        self.app = QApplication([])
        self.window = QWidget()
        self.window.setWindowTitle("Wyświetlacz STEP z obracaniem (refactor)")
        self.window.resize(1024, 768)
        self.layout = QVBoxLayout(self.window)
        self.viewer = qtViewer3d(self.window)
        self.layout.addWidget(self.viewer)
        self.display = self.viewer._display
        self.display.set_bg_gradient_color(rgb_color(0.68, 0.85, 0.90), rgb_color(0.95, 0.97, 1.0), 4)

        # UI: slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(360)
        self.slider.setValue(0)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.layout.addWidget(self.slider)

        # init defaults
        self._init_defaults()

    # -------------------------
    # Cache helpers
    # -------------------------
    def _get_cache_key(self) -> str:
        """Generuje hash na podstawie ścieżek plików + mtime (jeśli plik istnieje)."""
        h = hashlib.md5()
        for p in self.filenames:
            if p.exists():
                mtime = p.stat().st_mtime
                h.update(f"{str(p.resolve())}:{mtime}".encode())
            else:
                h.update(f"{str(p.resolve())}:missing".encode())
        return h.hexdigest()

    def _get_cache_path(self) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        name = f"shapes_cache_{self._get_cache_key()}.pkl"
        return self.cache_dir / name

    def _load_cache(self) -> Optional[Tuple[List, List]]:
        cache_path = self._get_cache_path()
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

    def _save_cache(self, shapes: List, statuses: List) -> None:
        cache_path = self._get_cache_path()
        try:
            with cache_path.open("wb") as f:
                pickle.dump({"shapes": shapes, "statuses": statuses}, f)
            logger.info("Zapisano cache: %s", cache_path)
        except Exception as e:
            logger.warning("Nie udało się zapisać cache: %s", e)

    # -------------------------
    # Loading STEP
    # -------------------------
    def _read_step_files(self) -> Tuple[Optional[List], List]:
        """Wczytaj STEPy i zwróć (shapes, statuses)."""
        readers = []
        statuses = []
        for p in self.filenames:
            rdr = STEPControl_Reader()
            status = rdr.ReadFile(str(p))
            readers.append(rdr)
            statuses.append(status)
        # check statuses
        if not all(s == IFSelect_RetDone for s in statuses):
            logger.error("Jednen z plików nie został poprawnie wczytany: %s", statuses)
            return None, statuses
        shapes = []
        for rdr in readers:
            rdr.TransferRoots()
            shapes.append(rdr.Shape())
        return shapes, statuses

    

    # -------------------------
    # Geometry helpers
    # -------------------------
    @staticmethod
    def simplify_shapes(shapes: List, linear_deflection: float = 1.0, angular_deflection: float = 0.8) -> List:
        """Generuje meshe dla shape'ów (przy okazji zwraca oryginalne shapes)."""
        simplified = []
        for shp in shapes:
            mesh = BRepMesh_IncrementalMesh(shp, linear_deflection, True, angular_deflection)
            mesh.Perform()
            simplified.append(shp)
        return simplified

    @staticmethod
    def center_shapes(shapes: List) -> List:
        """Przesuwa każdy shape tak, żeby środek jego bounding box znalazł się w (0,0,0)."""
        centered = []
        for shape in shapes:
            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0
            cz = (zmin + zmax) / 2.0
            trsf = gp_Trsf()
            trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
            shp_centered = BRepBuilderAPI_Transform(shape, trsf, True).Shape()
            centered.append(shp_centered)
        return centered


    @staticmethod
    def apply_transform_to_shape(shape, transform: Optional[TransformType]):
        """Zastosuj rotacje i translacje do kształtu. Rotacje są względem (0,0,0)."""
        shp = shape
        if not transform:
            return shp

        rotations = transform.get("rotations", [])
        for rot in rotations:
            if not rot:
                continue
            axis = rot.get("axis")
            angle = rot.get("angle_deg")
            if axis and (angle is not None):
                ax_pnt = gp_Pnt(0, 0, 0)
                ax_dir = gp_Dir(*axis)
                ax = gp_Ax1(ax_pnt, ax_dir)
                rot_trsf = gp_Trsf()
                rot_trsf.SetRotation(ax, math.radians(float(angle)))
                shp = BRepBuilderAPI_Transform(shp, rot_trsf, True).Shape()

        tr = transform.get("translate")
        if tr:
            vec = gp_Vec(*tr)
            tr_trsf = gp_Trsf()
            tr_trsf.SetTranslation(vec)
            shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

        return shp
    
    @staticmethod   
    def apply_default_transforms(shapes, transforms_table):
        """
        Zastosuj transformacje (rotacje i translacje) dla wszystkich shape'ów
        zgodnie z istniejącą tabelą transforms_table, korzystając z funkcji
        apply_transform_to_shape().
        """
        if not shapes:
            print("⚠️ Brak shape'ów .")
            return shapes
        
        if not transforms_table:
            print("⚠️ Brak tabeli transformacji.")
            return shapes

        if len(shapes)!= len(transforms_table):
            print("⚠️ Liczba shape'ów i transformacji się nie zgadza.")
            return shapes


        transformed = []
        for i, shape in enumerate(shapes):
            new_shape = StepViewer.apply_transform_to_shape(shape, transforms_table[i])
            transformed.append(new_shape)

        print(f"✅ Zastosowano transformacje do {len(transformed)} brył.")
        return transformed

    def load_shapes(self) -> bool:
        """
        Ładuje kształty: najpierw próbuje z cache, jeśli brak -> wczytuje z plików i zapisuje cache.
        Zwraca True jeżeli kształty są poprawnie wczytane.
        """
        cached = self._load_cache()
        if cached:
            shapes, statuses = cached
            self.shapes = shapes
            self.statuses = statuses
            logger.info("Załadowano shapes z cache.")
        else:
            shapes, statuses = self._read_step_files()
            if shapes is None:
                logger.error("Nie udało się wczytać plików STEP.")
                return False
            self.raw_shapes = shapes
            self.statuses = statuses
            # automatyczna dalsza obróbka: meshing (simplify) i centrowanie
            self.simplified_shapes = self.simplify_shapes(self.raw_shapes)
            self.shapes = self.center_shapes(self.simplified_shapes)
            # zapis cache dla przyszłych uruchomień
            self._save_cache(shapes, statuses)


        # domyślne displayed
        self.displayed_shapes = self.apply_default_transforms(self.shapes, self.transforms_table)
        logger.info("Shapes gotowe do wyświetlenia: %d", len(self.shapes))
        return True




    # -------------------------
    # Drawing
    # -------------------------
    def redraw_scene(self) -> None:
        """Wyczyść scenę i narysuj ponownie wszystkie kształty wraz z markerem."""
        if self.display is None:
            logger.error("Display niedostępny.")
            return
        if not self.displayed_shapes:
            logger.warning("Brak shape'ów do wyświetlenia.")
            return

        self.display.EraseAll()
        for i, shp in enumerate(self.displayed_shapes):
            should_draw = self.draw_table[i] if i < len(self.draw_table) else True
            if should_draw:
                # czas rysowania (można mierzyć dla debugu)
                t0 = time.perf_counter()
                self.display.DisplayShape(shp, color=self.shape_colors[i])
                t1 = time.perf_counter()
                logger.debug("Rysowanie shape %d zajęło %.4f s", i, (t1 - t0))

        # marker w (0,0,0)
        marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), self.marker_radius).Shape()
        self.display.DisplayShape(marker, color=rgb_color(1.0, 0.0, 0.0))

        self.display.View_Iso()
        self.display.FitAll()
        try:
            self.display.View.Update()
        except Exception:
            # niektóre wersje mają inną metodę — ignore jeśli nie istnieje
            pass

    # -------------------------
    # UI callbacks / helpers
    # -------------------------
    def _on_slider_released(self) -> None:
        """Wywołanie po puszczeniu suwaka — aktualizuje kąt dla jednego elementu (idx=2)."""
        angle = float(self.slider.value())
        idx = 2  # zgodnie z Twoim oryginalnym kodem: 3. ramię (index 2)
        # zabezpieczenie
        if idx >= len(self.transforms_table):
            logger.warning("Brak transform_tabel dla indeksu %d", idx)
            return
        self.transforms_table[idx]["rotations"][0]["angle_deg"] = angle
        # zastosuj transform tylko do jednego shape'a, nie modyfikuj źródłowego centered shapes
        self.displayed_shapes[idx] = self.apply_transform_to_shape(self.shapes[idx], self.transforms_table[idx])
        self.redraw_scene()

    def _init_defaults(self):
        """Ustawienia domyślne (kolory, draw_table, transforms) zgodne z pierwotnym skryptem."""
        # kolory (jeśli shapes będą mniejsze/większe, v-sized list)
        logger.info("Inicjalizacja domyślnych ustawień viewer'a.")
        self.shape_colors = [
            rgb_color(0.6, 0.6, 0.6),
            rgb_color(0.4, 0.6, 1),
            rgb_color(0.4, 0.6, 1),
            rgb_color(0.4, 0.6, 1),
            rgb_color(0.6, 0.8, 0.4),
            rgb_color(0.6, 0.5, 0.9),
            rgb_color(0.9, 0.6, 0.4),
        ]
        # które elementy rysować (domyślnie: tylko index 2 jest True jak w Twoim przykładzie)
        self.draw_table = [False, False, True, False, False, False, False]

        # domyślne transforms (pusta translacja + dwie rotacje z kątem 0)
        self.transforms_table = [ {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                                  {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]}, 
                                ]

    # -------------------------
    # Run
    # -------------------------
    def run(self) -> None:
        if not self.load_shapes():
            logger.error("Koniec działania: nie udało się wczytać shapes.")
            return
        # pierwsze rysowanie
        self.redraw_scene()
        # pokaż okno i start event loop
        self.window.show()
        self.app.exec_()


# -------------------------
# Punkt wejścia
# -------------------------
if __name__ == "__main__":
    # Przykładowa lista plików (podstawić rzeczywiste ścieżki)
    filenames = [
        "ramie0.step", "ramie1.step", "ramie2.step",
        "ramie3.step", "ramie4.step", "ramie5.step", "ramie6.step",
    ]

    viewer = StepViewer(filenames=filenames, cache_dir=".cache", marker_radius=10.0)
    viewer.run()
