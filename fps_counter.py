import threading
import time

class FPSCounter:
    def __init__(self):
        self.frame_count = 0
        self.fps = 0
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self.thread = None

    def _update_fps(self):
        while not self._stop_event.wait(1.0):  # 使用 Event.wait 可被 stop 立即唤醒
            with self.lock:
                self.fps = self.frame_count
                self.frame_count = 0

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._update_fps, daemon=True)
        self.thread.start()

    def increment(self):
        with self.lock:
            self.frame_count += 1

    def get_fps(self):
        with self.lock:
            return self.fps

    def stop(self, timeout=1.0):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout)