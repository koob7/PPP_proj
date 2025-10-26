"""Manual control tab - 6 DOF control with sliders."""

from typing import Callable, Dict, Optional, List
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QComboBox,
)
from PyQt5.QtCore import Qt

from my_widget import ResettableSlider


class ManualControlTab(QWidget):
    """Tab for manual control of selected shape with 6 sliders (translation + rotation)."""
    
    def __init__(
        self,
        filenames: List[Path],
        current_shape_idx: int = 2,
        on_slider_change: Optional[Callable] = None,
        on_shape_selected: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.filenames = filenames
        self.current_shape_idx = current_shape_idx
        self.on_slider_change = on_slider_change
        self.on_shape_selected = on_shape_selected
        
        self.sliders_translate: Dict[str, QSlider] = {}
        self.sliders_rotate: Dict[str, QSlider] = {}
        self.shape_selector: Optional[QComboBox] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Shape selector combobox
        self.shape_selector = QComboBox()
        for i, f in enumerate(self.filenames):
            self.shape_selector.addItem(f"Shape {i} ({f.name})", i)
        self.shape_selector.setCurrentIndex(self.current_shape_idx)
        self.shape_selector.currentIndexChanged.connect(self._handle_shape_selected)
        layout.addWidget(self.shape_selector)
        
        # Translation sliders
        layout.addWidget(QLabel("Translacje (mm)"))
        for axis in ["X", "Y", "Z"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [mm]")
            val_lbl = QLabel("0")
            slider = ResettableSlider(Qt.Horizontal, default_value=0)
            slider.setMinimum(-600)
            slider.setMaximum(600)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(100)
            slider.setSingleStep(1)
            slider.setPageStep(10)
            slider.setObjectName(f"translate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.sliderReleased.connect(self._handle_slider_change)
            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            layout.addWidget(row)
            self.sliders_translate[axis] = slider
        
        # Rotation sliders
        layout.addWidget(QLabel("Rotacje (°)"))
        for axis in ["X", "Y", "Z"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            title_lbl = QLabel(f"{axis} [°]")
            val_lbl = QLabel("0")
            slider = ResettableSlider(Qt.Horizontal, default_value=0)
            slider.setMinimum(0)
            slider.setMaximum(360)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(30)
            slider.setSingleStep(1)
            slider.setPageStep(15)
            slider.setObjectName(f"rotate_{axis}")
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.sliderReleased.connect(self._handle_slider_change)
            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            layout.addWidget(row)
            self.sliders_rotate[axis] = slider
        
        layout.addStretch(1)
    
    def _handle_slider_change(self):
        """Internal handler that calls the external callback."""
        if self.on_slider_change:
            self.on_slider_change()
    
    def _handle_shape_selected(self, index: int):
        """Internal handler that calls the external callback."""
        self.current_shape_idx = index
        if self.on_shape_selected:
            self.on_shape_selected(index)
    
    def get_translation_values(self) -> tuple[float, float, float]:
        """Get current translation values from sliders."""
        return (
            self.sliders_translate["X"].value(),
            self.sliders_translate["Y"].value(),
            self.sliders_translate["Z"].value(),
        )
    
    def get_rotation_values(self) -> tuple[float, float, float]:
        """Get current rotation values from sliders (X, Y, Z order)."""
        return (
            self.sliders_rotate["X"].value(),
            self.sliders_rotate["Y"].value(),
            self.sliders_rotate["Z"].value(),
        )
    
    def set_translation_values(self, x: float, y: float, z: float):
        """Set translation slider values."""
        self.sliders_translate["X"].setValue(int(x))
        self.sliders_translate["Y"].setValue(int(y))
        self.sliders_translate["Z"].setValue(int(z))
    
    def set_rotation_values(self, x: float, y: float, z: float):
        """Set rotation slider values."""
        self.sliders_rotate["X"].setValue(int(x))
        self.sliders_rotate["Y"].setValue(int(y))
        self.sliders_rotate["Z"].setValue(int(z))
    
    def get_current_shape_index(self) -> int:
        """Get currently selected shape index."""
        return self.current_shape_idx
