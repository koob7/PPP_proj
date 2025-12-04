import threading
import time
from typing import Callable, Optional
import serial


class SerialManager:
    """Simple serial manager with background reader and callbacks.

    Usage:
      manager = SerialManager(port='COM3', baudrate=115200)
      manager.set_rx_callback(lambda b: print('RX:', b))
      manager.write(b'hello')
    """

    def __init__(self, port: str = 'COM3', baudrate: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._rx_cb: Optional[Callable[[bytes], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        try:
            self._ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except Exception:
            self._ser = None

    def is_open(self) -> bool:
        return bool(self._ser and self._ser.is_open)

    def set_rx_callback(self, cb: Callable[[bytes], None]) -> None:
        self._rx_cb = cb

    def start_reader(self) -> None:
        if not self.is_open() or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop_reader(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None

    def _reader_loop(self) -> None:
        while self._running and self._ser:
            try:
                data = self._ser.readline()
                if data:
                    if self._rx_cb:
                        try:
                            self._rx_cb(data)
                        except Exception:
                            pass
            except Exception:
                time.sleep(0.05)

    def write(self, data: bytes) -> bool:
        """Write bytes to serial. Returns True on success."""
        if not self._ser:
            return False
        try:
            self._ser.write(data)
            return True
        except Exception:
            return False

    def close(self) -> None:
        try:
            self.stop_reader()
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
