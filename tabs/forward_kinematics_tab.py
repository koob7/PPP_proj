"""Forward kinematics tab - control robot axes."""

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


class ForwardKinematicsTab(QWidget):
    """Tab for forward kinematics - control 6 robot axes."""
    
    def __init__(
        self,
        on_slider_change: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.on_slider_change = on_slider_change
        self.axis_sliders: Dict[int, QSlider] = {}
        self.pose_line = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Kinematyka prosta - sterowanie osiami robota")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        
        # Create 6 sliders for axes 1-6
        for i in range(1, 7):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            
            # Label for axis
            title_lbl = QLabel(f"Oś {i} [°]")
            title_lbl.setMinimumWidth(60)
            
            # Value label
            val_lbl = QLabel("0")
            val_lbl.setMinimumWidth(40)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Slider with resettable functionality
            slider = ResettableSlider(Qt.Horizontal, default_value=0)
            slider.setMinimum(-180)
            slider.setMaximum(180)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(30)
            slider.setSingleStep(1)
            slider.setPageStep(15)
            slider.setObjectName(f"axis_{i}")
            
            # Connect signals
            slider.valueChanged.connect(lambda v, lab=val_lbl: lab.setText(str(int(v))))
            slider.sliderReleased.connect(self._handle_slider_change)
            
            # Add widgets to row
            row_layout.addWidget(title_lbl)
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(val_lbl)
            
            layout.addWidget(row)
            self.axis_sliders[i] = slider

        # Pose display
        pose_title = QLabel("Pozycja robota (x, y, z, rot a, b, c)")
        pose_title.setStyleSheet("margin-top: 8px; font-weight: bold;")
        layout.addWidget(pose_title)

        pose_row = QWidget()
        pose_row_layout = QHBoxLayout(pose_row)
        pose_row_layout.setContentsMargins(0, 0, 0, 0)
        self.pose_line = QLineEdit()
        self.pose_line.setReadOnly(True)
        self.pose_line.setPlaceholderText("x: -, y: -, z: -, a: -, b: -, c: -")
        self.pose_line.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        pose_row_layout.addWidget(self.pose_line)
        layout.addWidget(pose_row)

        # Add stretch at the end
        layout.addStretch(1)
    
    def _handle_slider_change(self):
        """Handle slider change event."""
        if self.on_slider_change:
            self.on_slider_change()
    
    def get_axis_values(self) -> Tuple[float, float, float, float, float, float]:
        """Get current values of all 6 axes in degrees."""
        return tuple(self.axis_sliders[i].value() for i in range(1, 7))
    
    def set_axis_values(self, values: Tuple[float, float, float, float, float, float]):
        """Set values for all 6 axes."""
        for i, value in enumerate(values, start=1):
            slider = self.axis_sliders[i]
            slider.blockSignals(True)
            slider.setValue(int(value))
            slider.blockSignals(False)
    
    def reset_all_axes(self):
        """Reset all axes to 0."""
        self.set_axis_values((0, 0, 0, 0, 0, 0))

    # --- Pose display helpers ---
    def set_pose_numbers(self, x: float, y: float, z: float, a: float, b: float, c: float) -> None:
        """Display numeric pose values in the read-only field.

        Units convention (UI only): x,y,z in mm, a,b,c in degrees.
        """
        if self.pose_line is not None:
            self.pose_line.setText(
                f"x: {x:.2f}, y: {y:.2f}, z: {z:.2f}, a: {a:.2f}, b: {b:.2f}, c: {c:.2f}"
            )

    def set_pose_text(self, text: str) -> None:
        """Display arbitrary text in the pose field (e.g., when FK not implemented)."""
        if self.pose_line is not None:
            self.pose_line.setText(text)
