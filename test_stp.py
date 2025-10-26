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
from PyQt5.QtWidgets import (
    QApplication,
    QSlider,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QTabWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QCheckBox,
    QPushButton,
)
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

        self.current_shape_idx = 2  # domyślnie sterujemy shape o indexie 2

        # init defaults
        self._init_defaults()

        # PyQt / OCC display
        self.app = QApplication([])
        self.window = QWidget()
        self.window.setWindowTitle("Wyświetlacz STEP z obracaniem (refactor)")
        self.window.resize(1280, 1024)

        self.main_layout = QVBoxLayout(self.window)
        self.splitter = QSplitter(Qt.Vertical)

        # viewer 3D
        self.viewer = qtViewer3d(self.window)
        self.display = self.viewer._display
        self.display.set_bg_gradient_color(rgb_color(0.68, 0.85, 0.90), rgb_color(0.95, 0.97, 1.0), 4)
        self.splitter.addWidget(self.viewer)

        # zakładki sterowania
        tabs = QTabWidget()

        self.tab1 = QWidget()
        self.tab1_layout = QVBoxLayout(self.tab1)
        # combobox do wyboru sterowanego shape'u
        self.shape_selector = QComboBox()
        for i, f in enumerate(self.filenames):
            self.shape_selector.addItem(f"Shape {i} ({f.name})", i)
        self.shape_selector.setCurrentIndex(self.current_shape_idx)
        self.shape_selector.currentIndexChanged.connect(self._on_shape_selected)
        self.tab1_layout.addWidget(self.shape_selector)

        # translacje (z podpisami)
        self.tab1_layout.addWidget(QLabel("Translacje (mm)"))
        self.sliders_translate = {}
        for axis in ["X", "Y", "Z"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [mm]")
            val_lbl = QLabel("0")
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(-600)
            slider.setMaximum(600)
            slider.setValue(0)
            slider.setObjectName(f"translate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.sliderReleased.connect(self._on_manual_slider_change)
            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            self.tab1_layout.addWidget(row)
            self.sliders_translate[axis] = slider

        # rotacje (z podpisami)
        self.tab1_layout.addWidget(QLabel("Rotacje (°)"))
        self.sliders_rotate = {}
        for axis in ["X", "Y", "Z"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [°]")
            val_lbl = QLabel("0")
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(360)
            slider.setValue(0)
            slider.setObjectName(f"rotate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.sliderReleased.connect(self._on_manual_slider_change)
            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            self.tab1_layout.addWidget(row)
            self.sliders_rotate[axis] = slider

        tabs.addTab(self.tab1, "ruch testowy")
        tabs.addTab(QWidget(), "sterowanie osiami")
        tabs.addTab(QWidget(), "kinematyka prosta")
        tabs.addTab(QWidget(), "kinematyka odwrotna")
        # globalna zakładka widoczności elementów
        visibility_tab = QWidget()
        vlayout = QVBoxLayout(visibility_tab)
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.addWidget(QLabel("Widoczność elementów:"))
        btn_all = QPushButton("Zaznacz wszystko")
        btn_none = QPushButton("Odznacz wszystko")
        btn_all.clicked.connect(lambda: self._set_all_visibility(True))
        btn_none.clicked.connect(lambda: self._set_all_visibility(False))
        header_layout.addWidget(btn_all)
        header_layout.addWidget(btn_none)
        header_layout.addStretch(1)
        vlayout.addWidget(header_row)
        # lista checkboxów
        self.visibility_checkboxes = []

        for i in range(len(self.filenames)):
            name = None
            try:
                if self.filenames and i < len(self.filenames):
                    name = self.filenames[i].name
            except Exception:
                name = None
            text = f"{i}: {name}" if name else f"{i}"
            cb = QCheckBox(text)
            checked = bool(self.draw_table[i])
            cb.setChecked(checked)
            cb.stateChanged.connect(lambda state, idx=i: self._on_visibility_changed(idx, state))
            vlayout.addWidget(cb)
            self.visibility_checkboxes.append(cb)
        tabs.addTab(visibility_tab, "widoczność elementów")
        self.splitter.addWidget(tabs)

        # Ustaw domyślną wysokość viewer 3D na 600 px, reszta niech się dostosuje
        try:
            bottom_h = max(100, self.window.height() - 600)
            self.splitter.setSizes([600, bottom_h])
        except Exception:
            self.splitter.setStretchFactor(0, 4)
            self.splitter.setStretchFactor(1, 1)

        self.main_layout.addWidget(self.splitter)


        # po ustawieniu domyślnych wartości zsynchronizuj checkboxy widoczności z draw_table
        try:
            self._sync_visibility_checkboxes()
        except Exception:
            pass

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
            self._save_cache(self.shapes, statuses)


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
 # -------------------------
    # UI callbacks
    # -------------------------
    def _on_manual_slider_change(self):
        idx = self.current_shape_idx
        if idx >= len(self.transforms_table):
            return
        tr_x = self.sliders_translate["X"].value()
        tr_y = self.sliders_translate["Y"].value()
        tr_z = self.sliders_translate["Z"].value()
        self.transforms_table[idx]["translate"] = (tr_x, tr_y, tr_z)
        rx = self.sliders_rotate["X"].value()
        ry = self.sliders_rotate["Y"].value()
        rz = self.sliders_rotate["Z"].value()
        self.transforms_table[idx]["rotations"][0]["angle_deg"] = rz
        self.transforms_table[idx]["rotations"][1]["angle_deg"] = ry
        self.transforms_table[idx]["rotations"][2]["angle_deg"] = rx
        self.displayed_shapes[idx] = self.apply_transform_to_shape(self.shapes[idx], self.transforms_table[idx])
        self.redraw_scene()

    def _on_shape_selected(self, index):
        self.current_shape_idx = index
        if index >= len(self.transforms_table):
            return
        tr = self.transforms_table[index].get("translate", (0, 0, 0))
        self.sliders_translate["X"].setValue(int(tr[0]))
        self.sliders_translate["Y"].setValue(int(tr[1]))
        self.sliders_translate["Z"].setValue(int(tr[2]))
        rotations = self.transforms_table[index]["rotations"]
        self.sliders_rotate["Z"].setValue(int(rotations[0]["angle_deg"]))
        self.sliders_rotate["Y"].setValue(int(rotations[1]["angle_deg"]))
        self.sliders_rotate["X"].setValue(int(rotations[2]["angle_deg"]))

    def _on_visibility_changed(self, idx: int, state: int) -> None:
        # aktualizacja widoczności i odrysowanie sceny
        val = (state == Qt.Checked)
        if not self.draw_table:
            self.draw_table = []
        if idx >= len(self.draw_table):
            self.draw_table += [False] * (idx + 1 - len(self.draw_table))
        self.draw_table[idx] = val
        self.redraw_scene()

    def _set_all_visibility(self, value: bool) -> None:
        # ustawienie widoczności dla wszystkich elementów
        count = len(self.visibility_checkboxes) if hasattr(self, 'visibility_checkboxes') else 0
        if count == 0:
            return
        if not self.draw_table or len(self.draw_table) < count:
            self.draw_table = (self.draw_table or []) + [False] * (count - len(self.draw_table or []))
        for i in range(count):
            self.draw_table[i] = value
            cb = self.visibility_checkboxes[i]
            bs = cb.blockSignals(True)
            try:
                cb.setChecked(value)
            finally:
                cb.blockSignals(bs)
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

        # domyślne transforms (pusta translacja + trzy rotacje: Z, Y, X)
        self.transforms_table = [
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},  # Z
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},  # Y
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},  # X
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,0,0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
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
