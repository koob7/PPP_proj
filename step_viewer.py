# pythonOCC / OCC imports
import os
from OCC.Display.backend import load_backend
load_backend("pyqt5")

from OCC.Display.qtDisplay import qtViewer3d
from OCC.Core.Quantity import Quantity_Color, Quantity_NOC_BLACK
from OCC.Core.V3d import V3d_WIREFRAME
from OCC.Core.Aspect import Aspect_TOTP_RIGHT_LOWER
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Display.OCCViewer import rgb_color
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.AIS import AIS_Shape
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from geometry_helper import apply_transform_to_shape, apply_default_transforms, get_total_transform
import math
import numpy as np

import socket
import struct

APP_PORT = 6002
APP_IP = '127.0.0.1'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send(robot_id, a1, a2, a3, a4, a5, a6):
    sock.sendto(struct.pack('<II6f', 2, robot_id, np.deg2rad(a1)-np.pi/2, np.deg2rad(a2)-np.pi/2, np.deg2rad(a3)-np.pi/2, np.deg2rad(a4)-np.pi/2, np.deg2rad(a5), np.deg2rad(a6)), (APP_IP, APP_PORT))


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
from my_types import TransformType, sum_transforms
from tabs import (
    ManualControlTab,
    VisibilityTab,
    AxisControlTab,
    ForwardKinematicsTab,
    InverseKinematicsTab,
)
from fk_helper import ROBOT_DH_PARAMS, dh_matrix, mat4_mul, pose_from_transform, calculate_ik, calculate_ik2

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
        self.displayed_shapes = {}
        self.shapes_with_transforms: Optional[List] = None
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
        self.context = self.display.Context
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
        
        # Forward kinematics tab
        self.forward_kinematics_tab = ForwardKinematicsTab(
            on_slider_released=self._on_forward_kinematics_released,
            on_slider_change=self._on_forward_kinematics_change,
        )
        tabs.addTab(self.forward_kinematics_tab, "kinematyka prosta")
        
        # Inverse kinematics tab
        self.inverse_kinematics_tab = InverseKinematicsTab(
            on_slider_released=self._on_inverse_kinematics_released,
            on_slider_change=self._on_inverse_kinematics_change,
        )
        tabs.addTab(self.inverse_kinematics_tab, "kinematyka odwrotna")
        
        # Visibility tab
        self.visibility_tab = VisibilityTab(
            filenames=self.filenames,
            draw_table=self.draw_table,
            on_visibility_changed=self._on_visibility_changed,
            on_set_all_visibility=self._set_all_visibility,
        )
        tabs.addTab(self.visibility_tab, "widoczność elementów")
        self.splitter.addWidget(tabs)
        tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs = tabs

        # Ustaw domyślną wysokość viewer 3D na 600 px, reszta niech się dostosuje
        try:
            bottom_h = max(100, self.window.height() - 600)
            self.splitter.setSizes([600, bottom_h])
        except Exception:
            self.splitter.setStretchFactor(0, 4)
            self.splitter.setStretchFactor(1, 1)

        self.main_layout.addWidget(self.splitter)

        self._on_shape_selected(self.current_shape_idx)

        # po ustawieniu domyślnych wartości zsynchronizuj checkboxy widoczności z draw_table
        try:
            self._sync_visibility_checkboxes()
        except Exception:
            pass
        
        send(1,0,0,0,0,0,0)
        send(0,0,0,0,0,0,0)
        sock.sendto(struct.pack('<II3f', 1, 0, -30.0, 0.0, 0.0), (APP_IP, APP_PORT))

    
    # -------------------------
    # Run
    # -------------------------
    def run(self) -> None:
        self.shapes = StepLoader(self.filenames, self.cache_dir).load_shapes()
        if not self.shapes:
            logger.error("Koniec działania: nie udało się wczytać shapes.")
            return
        self.shapes_with_transforms = apply_default_transforms(self.shapes, self.default_transforms)
        for i, shape in enumerate(self.shapes_with_transforms):
            self.displayed_shapes[i] = AIS_Shape(shape)

        # pierwsze rysowanie
        self.draw_scene()
        # pokaż okno i start event loop
        self.window.show()
        self.app.exec_()


    def update_shape(self, index: int) -> None:
        """Update shape at given index with new transform."""
        if index not in self.displayed_shapes:
            logger.error(f"Shape o indeksie {index} nie istnieje w displayed_shapes.")
            return
        if not self.draw_table[index]:
            self.context.Erase(self.displayed_shapes[index], True)
        else:
            self.context.Display(self.displayed_shapes[index], True)
            self.displayed_shapes[index].SetLocalTransformation(get_total_transform(self.transforms_table[index]))
            self.context.Redisplay(self.displayed_shapes[index], True)



    # -------------------------
    # Drawing
    # -------------------------
    def draw_scene(self) -> None:
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
                self.context.Display(self.displayed_shapes[i], False)
                self.context.SetColor(self.displayed_shapes[i], self.shape_colors[i], False)
                self.context.Redisplay(self.displayed_shapes[i], True)
                t1 = time.perf_counter()
                logger.debug("Rysowanie shape %d zajęło %.4f s", i, (t1 - t0))

        self._draw_axes()

        self.display.View_Iso()
        self.display.FitAll()
        try:
            self.display.View.Update()
        except Exception:
            # niektóre wersje mają inną metodę — ignore jeśli nie istnieje
            pass

    # --------------------------------------------------
    def _draw_axes(self):
        """Pomocnicza metoda do rysowania osi XYZ."""
        axis_len = 400
        # X
        x_axis = BRepBuilderAPI_MakeEdge(gp_Pnt(-axis_len, 0, 0), gp_Pnt(axis_len, 0, 0)).Edge()
        self.display.DisplayShape(x_axis, color=rgb_color(1.0, 0.0, 0.0))
        # Y
        y_axis = BRepBuilderAPI_MakeEdge(gp_Pnt(0, -axis_len, 0), gp_Pnt(0, axis_len, 0)).Edge()
        self.display.DisplayShape(y_axis, color=rgb_color(0.0, 1.0, 0.0))

        y_axis = BRepBuilderAPI_MakeEdge(gp_Pnt(250, -axis_len, 0), gp_Pnt(250, axis_len, 0)).Edge()
        self.display.DisplayShape(y_axis, color=rgb_color(0.0, 1.0, 0.0))
        # Z
        z_axis = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, -axis_len), gp_Pnt(0, 0, axis_len)).Edge()
        self.display.DisplayShape(z_axis, color=rgb_color(0.0, 0.0, 1.0))

        z_axis = BRepBuilderAPI_MakeEdge(gp_Pnt(250, 0, -axis_len), gp_Pnt(250, 0, axis_len)).Edge()
        self.display.DisplayShape(z_axis, color=rgb_color(0.0, 0.0, 1.0))
        # marker
        marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), self.marker_radius).Shape()
        self.display.DisplayShape(marker, color=rgb_color(1.0, 0.0, 0.0))

        marker = BRepPrimAPI_MakeSphere(gp_Pnt(250, 0, 0), self.marker_radius).Shape()
        self.display.DisplayShape(marker, color=rgb_color(1.0, 0.0, 0.0))


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

        self.update_shape(idx)
        self.forward_kinematics_tab.clear_pose()

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

    def apply_forward_kinematics(self, axis_values, verbos) -> Tuple[float, float, float, float, float, float]:
        """Handle forward kinematics slider changes."""
        self.forward_kinematics_tab.set_axis_values(tuple(round(v) for v in axis_values))

        # Convert to list if tuple (tuples are immutable)
        axis_values = list(axis_values)

        send(1, *axis_values)

        for i in range(6):
            axis_values[i] += 0.01 #to prevent singularity

        logger.info(f"Kinematyka prosta - wartości osi: {np.float32(axis_values)}")
        print("Joint 0 pos: x=0.00, y=0.00, z=0.00, a=0.00, b=0.00, c=0.00")


        dh = np.array([np.eye(4) for _ in range(6)])
        tr = np.array([np.eye(4) for _ in range(6)])

        for i in range(6):
            dh[i] = dh_matrix(ROBOT_DH_PARAMS[i][0], ROBOT_DH_PARAMS[i][1], ROBOT_DH_PARAMS[i][2], math.radians(axis_values[i]))

        tr[0] = dh[0]
        for i in range(1,6):
            tr[i] = mat4_mul(tr[i-1], dh[i])


        pos = 0, 0, 0, 0, 0, 0

        for i in range(0,6):
            pos2 = pose_from_transform(tr[i], degrees=True)
            if(verbos):
                x, y, z, a, b, c = pos
                x2, y2, z2, a2, b2, c2 = pos2
                self.transforms_table[i+1]['translate'] = (x, y, z)
                self.transforms_table[i+1]['rotations'][0]['angle_deg'] = a2  # Z
                self.transforms_table[i+1]['rotations'][1]['angle_deg'] = b2  # Y 
                self.transforms_table[i+1]['rotations'][2]['angle_deg'] = c2  # X
                self.update_shape(i+1)
                print(f"Joint {i+1} pos: x={x:.2f}, y={y:.2f}, z={z:.2f}, a={a2:.2f}, b={b2:.2f}, c={c2:.2f}")
            pos = pos2


        P = np.array([
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 1]
        ])

        tr[5] = tr[5] @ P


        pos = pose_from_transform(tr[5], degrees=True)
        x, y, z, a, b, c = pos
        self.forward_kinematics_tab.set_pose_numbers(x, y, z, a, b, c) # Z Y X

        o1, o2, o3, o4, o5, o6 = calculate_ik2(x, y, z, a, b, c)
        send(0, o1, o2, o3, o4, o5, o6)
        return pos

    def _on_forward_kinematics_released(self) -> None:
        """Handle forward kinematics slider changes."""
        x, y, z, a, b, c = self.apply_forward_kinematics(list(self.forward_kinematics_tab.get_axis_values()), True)
        self.inverse_kinematics_tab.set_pose_desired_numbers(x, y, z, a, b, c)
        self.inverse_kinematics_tab.set_pose_achieved_numbers(x, y, z, a, b, c)
        self.inverse_kinematics_tab.set_target_pose_values((x, y, z, a, b, c))

    def _on_inverse_kinematics_released(self) -> None:
        """Handle inverse kinematics target changes and update robot pose."""
        if not hasattr(self, "inverse_kinematics_tab"):
            return
        
        # Pobierz zadaną pozycję z suwaków IK
        x, y, z, a, b, c = self.inverse_kinematics_tab.get_target_pose_values()
        
        try:
            # Oblicz kąty osi z kinematyki odwrotnej
            o1, o2, o3, o4, o5, o6 = calculate_ik2(x, y, z, a, b, c)
            
            # Oblicz faktyczną osiągniętą pozycję przez kinematykę prostą
            x1, y1, z1, a1, b1, c1 = self.apply_forward_kinematics((o1, o2, o3, o4, o5, o6), True)
            send(0, o1, o2, o3, o4, o5, o6)
            
            # Zaktualizuj wyświetlane pola
            self.inverse_kinematics_tab.set_pose_desired_numbers(x, y, z, a, b, c)
            self.inverse_kinematics_tab.set_pose_achieved_numbers(x1, y1, z1, a1, b1, c1)
            self.forward_kinematics_tab.set_pose_numbers(x1, y1, z1, a1, b1, c1)
            
            # Zaktualizuj suwaki kinematyki prostej z obliczonymi kątami
            self.forward_kinematics_tab.set_axis_values((o1, o2, o3, o4, o5, o6))

            
            logger.info(f"IK solved: θ=({o1:.2f}, {o2:.2f}, {o3:.2f}, {o4:.2f}, {o5:.2f}, {o6:.2f})°")
            
        except Exception as e:
            logger.error(f"Błąd obliczania IK: {e}")
            # W razie błędu pokaż zerowe wartości
            self.inverse_kinematics_tab.set_pose_achieved_numbers(0, 0, 0, 0, 0, 0)



    def _on_forward_kinematics_change(self) -> None:
        x, y, z, a, b, c = self.apply_forward_kinematics(list(self.forward_kinematics_tab.get_axis_values()), False)
        o1, o2, o3, o4, o5, o6 = calculate_ik2(x, y, z, a, b, c)
        send(0, o1, o2, o3, o4, o5, o6)

    
    def _on_inverse_kinematics_change(self) -> None:
        o1, o2, o3, o4, o5, o6 = calculate_ik2(*self.inverse_kinematics_tab.get_target_pose_values())
        send(0, o1, o2, o3, o4, o5, o6)

    def _on_visibility_changed(self, idx: int, state: int) -> None:
        # aktualizacja widoczności i odrysowanie sceny
        val = (state == Qt.Checked)
        if not self.draw_table:
            self.draw_table = []
        if idx >= len(self.draw_table):
            self.draw_table += [False] * (idx + 1 - len(self.draw_table))
        self.draw_table[idx] = val
        self.update_shape(idx)

    def _set_all_visibility(self, value: bool) -> None:
        """Set visibility for all elements."""
        count = len(self.filenames)
        if not self.draw_table or len(self.draw_table) < count:
            self.draw_table = (self.draw_table or []) + [False] * (count - len(self.draw_table or []))
        
        for i in range(count):
            self.draw_table[i] = value
            self.update_shape(i)
        
        self.visibility_tab.set_all_checkboxes(value)
    
    def _sync_visibility_checkboxes(self):
        """Sync visibility checkboxes with draw_table."""
        self.visibility_tab.sync_checkboxes(self.draw_table)

    def _on_tab_changed(self, index: int) -> None:
        """Wywołuje callback po zmianie zakładki."""
        widget = self.tabs.widget(index)
        if widget is self.manual_tab:
            # Wywołaj callback po wejściu w zakładkę manual_tab
            self._on_shape_selected(self.current_shape_idx)


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
        self.draw_table = [True, True, True, True, True, True, True]

        # domyślne transforms (pusta translacja + trzy rotacje: Z, Y, X)
        self.default_transforms = [
            {'translate': (0,0,65.6/2), 'rotations': [                 # X, Y, Z
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0},  # Z
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},  # Y
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 180},# X
            ]},
            {'translate': (0,60.90+82.9/2,3.04), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': -180},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (128.55,0,(39.40+38.9/2-3.5)), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 90},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
            {'translate': (0,12,32.55), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': -180},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 180},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': -90},
            ]},
            {'translate': (0,-(37+288/2),0), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg':-90},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': -90},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': -90},
            ]},
            {'translate': (0,0,18.2), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': -180},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': -90},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 90},
            ]},
            {'translate': (0,0,9/2+54.4), 'rotations': [
                {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': -90},
                {'origin': (0,0,0), 'axis': (0,1,0), 'angle_deg': 0},
                {'origin': (0,0,0), 'axis': (1,0,0), 'angle_deg': 0},
            ]},
        ]


        # ułożenie jedynek w macierzy określa konwencję kolejnych obrotów
        self.transforms_table  = [
            {
                'translate': (0.0, 0.0, 0.0),
                'rotations': [
                    {'origin': (0, 0, 0), 'axis': (1, 0, 0), 'angle_deg': 0.0},  # Z
                    {'origin': (0, 0, 0), 'axis': (0, 1, 0), 'angle_deg': 0.0},  # Y
                    {'origin': (0, 0, 0), 'axis': (0, 0, 1), 'angle_deg': 0.0},  # X
                ],
            }
            for _ in range(7)
        ]

    