"""Visibility control tab - show/hide individual shapes."""

from typing import Callable, List, Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
)
from PyQt5.QtCore import Qt


class VisibilityTab(QWidget):
    """Tab for controlling visibility of individual shapes."""
    
    def __init__(
        self,
        filenames: List[Path],
        draw_table: List[bool],
        on_visibility_changed: Optional[Callable[[int, int], None]] = None,
        on_set_all_visibility: Optional[Callable[[bool], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.filenames = filenames
        self.draw_table = draw_table
        self.on_visibility_changed = on_visibility_changed
        self.on_set_all_visibility = on_set_all_visibility
        
        self.visibility_checkboxes: List[QCheckBox] = []
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header with select all/none buttons
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.addWidget(QLabel("Widoczność elementów:"))
        
        btn_all = QPushButton("Zaznacz wszystko")
        btn_none = QPushButton("Odznacz wszystko")
        btn_all.clicked.connect(lambda: self._handle_set_all_visibility(True))
        btn_none.clicked.connect(lambda: self._handle_set_all_visibility(False))
        
        header_layout.addWidget(btn_all)
        header_layout.addWidget(btn_none)
        header_layout.addStretch(1)
        layout.addWidget(header_row)
        
        # Checkboxes for each shape
        for i in range(len(self.filenames)):
            name = None
            try:
                if self.filenames and i < len(self.filenames):
                    name = self.filenames[i].name
            except Exception:
                name = None
            
            text = f"{i}: {name}" if name else f"{i}"
            cb = QCheckBox(text)
            checked = bool(self.draw_table[i]) if i < len(self.draw_table) else False
            cb.setChecked(checked)
            cb.stateChanged.connect(lambda state, idx=i: self._handle_visibility_changed(idx, state))
            layout.addWidget(cb)
            self.visibility_checkboxes.append(cb)
        
        layout.addStretch(1)
    
    def _handle_visibility_changed(self, idx: int, state: int):
        """Internal handler that calls the external callback."""
        if self.on_visibility_changed:
            self.on_visibility_changed(idx, state)
    
    def _handle_set_all_visibility(self, value: bool):
        """Internal handler that calls the external callback."""
        if self.on_set_all_visibility:
            self.on_set_all_visibility(value)
    
    def sync_checkboxes(self, draw_table: List[bool]):
        """Sync checkbox states with draw_table without emitting signals."""
        for i, cb in enumerate(self.visibility_checkboxes):
            if i < len(draw_table):
                cb.blockSignals(True)
                try:
                    cb.setChecked(draw_table[i])
                finally:
                    cb.blockSignals(False)
    
    def set_all_checkboxes(self, value: bool):
        """Set all checkboxes to a value without emitting signals."""
        for cb in self.visibility_checkboxes:
            cb.blockSignals(True)
            try:
                cb.setChecked(value)
            finally:
                cb.blockSignals(False)
