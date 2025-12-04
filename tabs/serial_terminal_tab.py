from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt


class SerialTerminalTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        self.layout.addWidget(self.log)

        h = QHBoxLayout()
        self.input = QLineEdit(self)
        self.send_btn = QPushButton('Send', self)
        h.addWidget(self.input)
        h.addWidget(self.send_btn)
        self.layout.addLayout(h)

        self.send_btn.clicked.connect(self._on_send_clicked)

        self._send_callback = None

    def _on_send_clicked(self):
        txt = self.input.text()
        if not txt:
            return
        if self._send_callback:
            # send raw bytes with newline
            try:
                self._send_callback(txt.encode('utf-8') + b"\n")
                self.append_tx(txt)
            except Exception:
                pass
        else:
            self.append_tx(txt)
        self.input.clear()

    def set_send_callback(self, cb):
        self._send_callback = cb

    def append_rx(self, data: bytes):
        try:
            s = data.decode('utf-8', errors='replace')
        except Exception:
            s = str(data)
        self.log.append(f"RX: {s}")

    def append_tx(self, text: str):
        self.log.append(f"TX: {text}")
