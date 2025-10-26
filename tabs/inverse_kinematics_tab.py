"""Inverse kinematics tab - placeholder for future implementation."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class InverseKinematicsTab(QWidget):
    """Placeholder tab for inverse kinematics functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize placeholder UI."""
        layout = QVBoxLayout(self)
        label = QLabel("Kinematyka odwrotna - do implementacji")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
        layout.addStretch(1)
