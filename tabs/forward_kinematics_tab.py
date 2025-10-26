"""Forward kinematics tab - placeholder for future implementation."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class ForwardKinematicsTab(QWidget):
    """Placeholder tab for forward kinematics functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize placeholder UI."""
        layout = QVBoxLayout(self)
        label = QLabel("Kinematyka prosta - do implementacji")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
        layout.addStretch(1)
