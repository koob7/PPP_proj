"""Inverse kinematics tab - target pose controls and readouts."""

from typing import Callable, Dict, Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QLineEdit,
)
from PyQt5.QtCore import Qt

from my_widget import ResettableSlider


class InverseKinematicsTab(QWidget):
    """Tab for inverse kinematics: set a desired pose (x,y,z,a,b,c) and view achieved pose."""

    def __init__(
        self,
        on_slider_released: Optional[Callable] = None,
        on_slider_change: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.on_slider_released = on_slider_released
        self.on_slider_change = on_slider_change
        self.sliders_translate: Dict[str, QSlider] = {}
        self.sliders_rotate: Dict[str, QSlider] = {}
        self.pose_desired_line: Optional[QLineEdit] = None
        self.pose_achieved_line: Optional[QLineEdit] = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components for IK target pose and readouts."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Kinematyka odwrotna - pozycja zadana")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)

        # Translation sliders (target X, Y, Z)
        layout.addWidget(QLabel("Translacje docelowe (mm)"))
        for axis in ["X", "Y", "Z"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [mm]")
            title_lbl.setMinimumWidth(60)
            val_lbl = QLabel("0")
            val_lbl.setMinimumWidth(60)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            slider = ResettableSlider(Qt.Horizontal, default_value=0)
            slider.setMinimum(-600)
            slider.setMaximum(600)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(100)
            slider.setSingleStep(1)
            slider.setPageStep(10)
            slider.setObjectName(f"ik_translate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.valueChanged.connect(self._handle_slider_change)
            slider.sliderReleased.connect(self._handle_slider_released)

            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            layout.addWidget(row)
            self.sliders_translate[axis] = slider

        # Rotation sliders (target A,B,C in degrees)
        layout.addWidget(QLabel("Rotacje docelowe (°) - A,B,C"))
        for axis in ["A", "B", "C"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [°]")
            title_lbl.setMinimumWidth(60)
            val_lbl = QLabel("0")
            val_lbl.setMinimumWidth(60)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            slider = ResettableSlider(Qt.Horizontal, default_value=0)
            slider.setMinimum(-180)
            slider.setMaximum(180)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(30)
            slider.setSingleStep(1)
            slider.setPageStep(15)
            slider.setObjectName(f"ik_rotate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.valueChanged.connect(self._handle_slider_change)
            slider.sliderReleased.connect(self._handle_slider_released)

            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            layout.addWidget(row)
            self.sliders_rotate[axis] = slider

        # Pose readouts
        pose_title_des = QLabel("Pozycja zadana (x, y, z, rot a, b, c)")
        pose_title_des.setStyleSheet("margin-top: 8px; font-weight: bold;")
        layout.addWidget(pose_title_des)

        pose_row_des = QWidget()
        pose_row_des_layout = QHBoxLayout(pose_row_des)
        pose_row_des_layout.setContentsMargins(0, 0, 0, 0)
        self.pose_desired_line = QLineEdit()
        self.pose_desired_line.setReadOnly(True)
        self.pose_desired_line.setPlaceholderText("x: -, y: -, z: -, a: -, b: -, c: -")
        self.pose_desired_line.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        pose_row_des_layout.addWidget(self.pose_desired_line)
        layout.addWidget(pose_row_des)

        pose_title_ach = QLabel("Pozycja osiągnięta (x, y, z, rot a, b, c)")
        pose_title_ach.setStyleSheet("margin-top: 4px; font-weight: bold;")
        layout.addWidget(pose_title_ach)

        pose_row_ach = QWidget()
        pose_row_ach_layout = QHBoxLayout(pose_row_ach)
        pose_row_ach_layout.setContentsMargins(0, 0, 0, 0)
        self.pose_achieved_line = QLineEdit()
        self.pose_achieved_line.setReadOnly(True)
        self.pose_achieved_line.setPlaceholderText("x: -, y: -, z: -, a: -, b: -, c: -")
        self.pose_achieved_line.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        pose_row_ach_layout.addWidget(self.pose_achieved_line)
        layout.addWidget(pose_row_ach)

        # Initialize readout with current slider values
        self._refresh_desired_readout()

        layout.addStretch(1)

    # -----------------
    # Event handling
    # -----------------
    def _handle_slider_released(self):
        self._refresh_desired_readout()
        if self.on_slider_released:
            self.on_slider_released()

    def _handle_slider_change(self):
        self._refresh_desired_readout()
        if self.on_slider_change:
            self.on_slider_change()

    def _refresh_desired_readout(self) -> None:
        x, y, z, a, b, c = self.get_target_pose_values()
        self.set_pose_desired_numbers(x, y, z, a, b, c)

    # -----------------
    # Public API
    # -----------------
    def get_target_pose_values(self) -> Tuple[float, float, float, float, float, float]:
        """Return desired target pose from sliders: (x,y,z in mm, a,b,c in deg)."""
        x = self.sliders_translate["X"].value()
        y = self.sliders_translate["Y"].value()
        z = self.sliders_translate["Z"].value()
        a = self.sliders_rotate["A"].value()
        b = self.sliders_rotate["B"].value()
        c = self.sliders_rotate["C"].value()
        return (x, y, z, a, b, c)

    def set_target_pose_values(self, values: Tuple[float, float, float, float, float, float]) -> None:
        x, y, z, a, b, c = values
        self.sliders_translate["X"].setValue(int(x))
        self.sliders_translate["Y"].setValue(int(y))
        self.sliders_translate["Z"].setValue(int(z))
        self.sliders_rotate["A"].setValue(int(a))
        self.sliders_rotate["B"].setValue(int(b))
        self.sliders_rotate["C"].setValue(int(c))
        self._refresh_desired_readout()

    def reset_target_pose(self) -> None:
        self.set_target_pose_values((0, 0, 0, 0, 0, 0))

    # --- Pose display helpers ---
    def set_pose_desired_numbers(self, x: float, y: float, z: float, a: float, b: float, c: float) -> None:
        if self.pose_desired_line is not None:
            self.pose_desired_line.setText(
                f"x: {x:.2f}, y: {y:.2f}, z: {z:.2f}, a: {a:.2f}, b: {b:.2f}, c: {c:.2f}"
            )

    def set_pose_achieved_numbers(self, x: float, y: float, z: float, a: float, b: float, c: float) -> None:
        if self.pose_achieved_line is not None:
            self.pose_achieved_line.setText(
                f"x: {x:.2f}, y: {y:.2f}, z: {z:.2f}, a: {a:.2f}, b: {b:.2f}, c: {c:.2f}"
            )

    def clear_pose_fields(self) -> None:
        if self.pose_desired_line is not None:
            self.pose_desired_line.setText("x: -, y: -, z: -, a: -, b: -, c: -")
        if self.pose_achieved_line is not None:
            self.pose_achieved_line.setText("x: -, y: -, z: -, a: -, b: -, c: -")
