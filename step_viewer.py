# pythonOCC / OCC imports
from OCC.Display.backend import load_backend
load_backend("pyqt5")

from OCC.Display.qtDisplay import qtViewer3d
from OCC.Core.Quantity import Quantity_Color, Quantity_NOC_BLACK
from OCC.Core.V3d import V3d_WIREFRAME
from OCC.Core.Aspect import Aspect_TOTP_RIGHT_LOWER
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Display.OCCViewer import rgb_color
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from geometry_helper import apply_transform_to_shape, apply_default_transforms

# PyQt5
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QTabWidget,
)
from PyQt5.QtCore import Qt

from logger import logger
from shape import StepLoader
from my_types import TransformType
from tabs import (
    ManualControlTab,
    VisibilityTab,
    AxisControlTab,
    ForwardKinematicsTab,
    InverseKinematicsTab,
)

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
        self.displayed_shapes: Optional[List] = None
        self.default_transforms: List[TransformType] = []
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
        self.display.View.TriedronDisplay(Aspect_TOTP_RIGHT_LOWER, Quantity_Color(Quantity_NOC_BLACK), 0.25, V3d_WIREFRAME)
        self.splitter.addWidget(self.viewer)

        # zakładki sterowania
        tabs = QTabWidget()

        # Manual control tab
        self.manual_tab = ManualControlTab(
            filenames=self.filenames,
            current_shape_idx=self.current_shape_idx,
            on_slider_change=self._on_manual_slider_change,
            on_shape_selected=self._on_shape_selected,
        )
        tabs.addTab(self.manual_tab, "ruch testowy")
        
        # Placeholder tabs
        tabs.addTab(AxisControlTab(), "sterowanie osiami")
        tabs.addTab(ForwardKinematicsTab(), "kinematyka prosta")
        tabs.addTab(InverseKinematicsTab(), "kinematyka odwrotna")
        
        # Visibility tab
        self.visibility_tab = VisibilityTab(
            filenames=self.filenames,
            draw_table=self.draw_table,
            on_visibility_changed=self._on_visibility_changed,
            on_set_all_visibility=self._set_all_visibility,
        )
        tabs.addTab(self.visibility_tab, "widoczność elementów")
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
    # Run
    # -------------------------
    def run(self) -> None:
        self.shapes = StepLoader(self.filenames, self.cache_dir).load_shapes()
        if not self.shapes:
            logger.error("Koniec działania: nie udało się wczytać shapes.")
            return
        self.displayed_shapes = apply_default_transforms(self.shapes, self.default_transforms)
        # pierwsze rysowanie
        self.redraw_scene()
        # pokaż okno i start event loop
        self.window.show()
        self.app.exec_()



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
    # UI callbacks
    # -------------------------
    def _on_manual_slider_change(self):
        idx = self.manual_tab.get_current_shape_index()
        if idx >= len(self.transforms_table):
            return
        
        tr_x, tr_y, tr_z = self.manual_tab.get_translation_values()
        self.transforms_table[idx]["translate"] = (tr_x, tr_y, tr_z)
        
        rx, ry, rz = self.manual_tab.get_rotation_values()
        self.transforms_table[idx]["rotations"][0]["angle_deg"] = rz
        self.transforms_table[idx]["rotations"][1]["angle_deg"] = ry
        self.transforms_table[idx]["rotations"][2]["angle_deg"] = rx
        
        self.displayed_shapes[idx] = apply_transform_to_shape(self.shapes[idx], self.transforms_table[idx])
        self.redraw_scene()

    def _on_shape_selected(self, index):
        self.current_shape_idx = index
        if index >= len(self.transforms_table):
            return
        
        tr = self.transforms_table[index].get("translate", (0, 0, 0))
        self.manual_tab.set_translation_values(tr[0], tr[1], tr[2])
        
        rotations = self.transforms_table[index]["rotations"]
        self.manual_tab.set_rotation_values(
            rotations[2]["angle_deg"],  # X
            rotations[1]["angle_deg"],  # Y
            rotations[0]["angle_deg"],  # Z
        )

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
        """Set visibility for all elements."""
        count = len(self.filenames)
        if not self.draw_table or len(self.draw_table) < count:
            self.draw_table = (self.draw_table or []) + [False] * (count - len(self.draw_table or []))
        
        for i in range(count):
            self.draw_table[i] = value
        
        self.visibility_tab.set_all_checkboxes(value)
        self.redraw_scene()
    
    def _sync_visibility_checkboxes(self):
        """Sync visibility checkboxes with draw_table."""
        self.visibility_tab.sync_checkboxes(self.draw_table)

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
        self.default_transforms = [
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

        self.transforms_table = self.default_transforms

    