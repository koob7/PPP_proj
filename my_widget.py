from PyQt5.QtWidgets import QSlider
from PyQt5.QtCore import Qt

class ResettableSlider(QSlider):
    """QSlider that resets to a default value on double-click and emits sliderReleased."""
    def __init__(self, orientation, default_value=0, parent=None):
        super().__init__(orientation, parent)
        self._default_value = default_value

    def mousePressEvent(self, event):
        # Right-click resets to default and triggers the same path as releasing the slider
        if event.button() == Qt.RightButton:
            self.setValue(self._default_value)
            try:
                self.sliderReleased.emit()
            except Exception:
                pass
            event.accept()
            return
        super().mousePressEvent(event)
