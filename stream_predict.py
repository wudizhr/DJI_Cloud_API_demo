from ultralytics import YOLO
import cv2
from fps_counter import FPSCounter
import logging
import threading
import queue
import time
from DroneGeoLocator import DroneGeoLocator
from CluodAPI_Terminal_Client.fly_utils import FlightState

logging.getLogger("ultralytics").setLevel(logging.ERROR)

# 默认 RTMP 源（可通过类参数覆盖）
source = "rtmp://81.70.222.38:1935/live/Drone001"


class StreamPredictor:
    """将原有的 RTMP 读取 + 后台 YOLO 推理 + 叠加绘制 封装为可复用类。

    使用方式:
        predictor = StreamPredictor(rtmp_url)
        predictor.run()  # 阻塞直到用户按 'q' 或 stop()
        predictor.stop() # 可在外部调用以提前结束
    """

    def __init__(
        self,
        rtmp_url: str,
        model_normal_path: str = "model/yolo11s",
        model_drone_path: str = "model/air2air_det_db-yolo11s_i512_c2.pt",
        max_queue: int = 2,
        window_name: str = "RTMP Stream",
        drone_classes=(0,),
        normal_classes=(0, 2),
        show_window: bool = True,
        stop_event=None,
        flight_state: FlightState = None,
        writer=print
    ) -> None:
        self.rtmp_url = rtmp_url
        self.window_name = window_name
        self.show_window = show_window
        # 加载模型（懒加载可再扩展）
        self.model_normal = YOLO(model_normal_path)
        self.model_drone = YOLO(model_drone_path)
        self.drone_classes = list(drone_classes)
        self.normal_classes = list(normal_classes)

        # FPS 计数器
        self.fps_counter = FPSCounter(); self.fps_counter.start()
        self.inference_fps_counter = FPSCounter(); self.inference_fps_counter.start()

        # 共享状态与队列、线程控制
        self.frame_queue: queue.Queue = queue.Queue(maxsize=max_queue)
        # 支持传入跨进程 Event（如 mp.Event），用于父进程控制停止
        self.stop_event = stop_event or threading.Event()
        self.out_lock = threading.Lock()
        self.shared = {"detections": [], "ts": None}
        self.worker: threading.Thread | None = None
        self.cap: cv2.VideoCapture | None = None
        # 保存主循环线程句柄，便于非阻塞启动
        self.main_thread: threading.Thread | None = None
        self.locator = DroneGeoLocator(
            sensor_width_mm=8.5,      # 典型1/1.5英寸传感器
            sensor_height_mm=6.4,     # 典型1/1.5英寸传感器
            focal_length_mm=168.0,      # 长焦镜头
            image_width_px=8000,      # 4K图像宽度
            image_height_px=6000      # 4K图像高度
        ) 
        self.flight_state = flight_state or FlightState()
        self.writer = writer

    # --- 推理相关 ---
    def _run_inference_on_frame(self, frame):
        detections = []
        try:
            # drone 专注模型
            result_drone = self.model_drone(frame, imgsz=512, verbose=False, conf=0.5, classes=self.drone_classes)
            for box in result_drone[0].boxes:
                cls_id = int(box.cls[0]); conf = float(box.conf[0])
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                label = self.model_drone.names.get(cls_id, str(cls_id))
                detections.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "conf": conf})

            # 通用模型
            results_normal = self.model_normal(frame, classes=self.normal_classes, imgsz=512, verbose=False, vid_stride=1, conf=0.3)
            for box in results_normal[0].boxes:
                cls_id = int(box.cls[0]); conf = float(box.conf[0])
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                label = self.model_normal.names.get(cls_id, str(cls_id))
                detections.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "conf": conf})
        except Exception as e:
            self.writer(f"Inference error: {e}")
        return detections

    def _inference_worker(self):
        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            detections = self._run_inference_on_frame(frame)
            self.inference_fps_counter.increment()
            with self.out_lock:
                self.shared['detections'] = detections
                self.shared['ts'] = time.time()
            try:
                self.frame_queue.task_done()
            except Exception:
                pass

    def _start_worker(self):
        if self.worker and self.worker.is_alive():
            return
        self.worker = threading.Thread(target=self._inference_worker, daemon=True)
        self.worker.start()

    # --- 主循环 ---
    def run(self):
        self.cap = cv2.VideoCapture(self.rtmp_url)
        if not self.cap.isOpened():
            self.writer(f"错误: 无法打开RTMP流 {self.rtmp_url}")
            return
        self.writer(f"成功连接到RTMP流: {self.rtmp_url}")
        ret, frame = self.cap.read()
        self.locator.image_height = frame.shape[0]
        self.locator.image_width = frame.shape[1]
        self.writer(f"视频分辨率: {self.locator.image_width}x{self.locator.image_height}")
        self._start_worker()
        font = cv2.FONT_HERSHEY_SIMPLEX; scale = 0.8; thickness = 2; margin = 6
        try:
            while not self.stop_event.is_set():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.writer("无法读取帧或流已结束")
                    break
                self.fps_counter.increment()
                display = frame.copy()
                info_fps = f"FPS: {self.fps_counter.get_fps()}"
                info_inference_fps = f"Inference FPS: {self.inference_fps_counter.get_fps()}"
                (w1, h1), _ = cv2.getTextSize(info_fps, font, scale, thickness)
                (w2, h2), _ = cv2.getTextSize(info_inference_fps, font, scale, thickness)
                rect_w = max(w1, w2) + margin * 2
                rect_h = h1 + h2 + margin * 4
                cv2.rectangle(display, (5, 5), (5 + rect_w, 5 + rect_h), (0, 0, 0), -1)
                cv2.putText(display, info_fps, (10, 10 + h1), font, scale, (0, 255, 0), thickness)
                cv2.putText(display, info_inference_fps, (10, 10 + h1 + h2 + margin), font, scale, (0, 255, 255), thickness)
                with self.out_lock:
                    detections = list(self.shared.get('detections', []))
                if detections:
                    if self.show_window:
                        draw_detections(display, detections) 
                    self.get_target_pos(detections)                
                # 将帧送入推理队列（非阻塞）
                try:
                    self.frame_queue.put_nowait(frame.copy())
                except queue.Full:
                    pass
                if self.show_window:
                    # self.writer(self.show_window)
                    cv2.imshow(self.window_name, display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        except KeyboardInterrupt:
            self.writer("用户中断提取过程")
        except Exception as e:
            self.writer(f"发生错误: {e}")
        finally:
            self.stop()


    def stop(self):
        # 允许多次调用
        self.stop_event.set()
        try:
            if self.worker:
                self.worker.join(timeout=1.0)
        except Exception:
            pass
        if self.cap:
            self.cap.release()
        if self.show_window:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

    # --- 外部辅助获取当前检测结果 ---
    def get_latest_detections(self):
        with self.out_lock:
            return list(self.shared.get('detections', []))

    # --- 非阻塞启动与等待 ---
    def start_in_thread(self, daemon: bool = True):
        """在后台线程中启动 run()，使其不阻塞调用方。

        注意：再次调用会在已有线程存活时直接返回。
        """
        if self.main_thread and self.main_thread.is_alive():
            return self.main_thread
        t = threading.Thread(target=self.run, daemon=daemon)
        self.main_thread = t
        t.start()
        return t

    def join(self, timeout: float = 0.1):
        """等待后台主循环线程结束。"""
        if self.main_thread:
            self.main_thread.join(timeout=timeout)

    def get_target_pos(self, detections):
        """Draw detections on a frame (in-place)."""
        if self.flight_state.lat is None or self.flight_state.lon is None:
            self.writer("无人机GPS位置未知，无法计算目标经纬度")
            return
        for det in detections:
            x1, y1, x2, y2 = det['x1'], det['y1'], det['x2'], det['y2']
            center_point_x = int(x1 + (x2 - x1) / 2)
            center_point_y = int(y1 + (y2 - y1) / 2)
            label = det['label']
            conf = det['conf']
            display_text = f"{label} {conf:.2f}"
            target_lat, target_lon = self.locator.pixel_to_geo_coordinates(
                self.flight_state.lat, self.flight_state.lon,
                (self.flight_state.height - self.flight_state.takeoff_height),
                center_point_x, center_point_y, self.flight_state.attitude_head
            )
            self.writer(f"像素偏移: dx={center_point_x:.1f}, dy={center_point_y:.1f} 像素")
            self.writer(f"检测到 {display_text} at (lat: {target_lat}, lon: {target_lon})")
            self.writer(f"无人机当前位置 (lat: {self.flight_state.lat}, lon: {self.flight_state.lon}, alt: {self.flight_state.height - self.flight_state.takeoff_height} m, head: {self.flight_state.attitude_head}°)")

def draw_detections(frame, detections):
    """Draw detections on a frame (in-place)."""
    for det in detections:
        x1, y1, x2, y2 = det['x1'], det['y1'], det['x2'], det['y2']
        center_point_x = int(x1 + (x2 - x1) / 2)
        center_point_y = int(y1 + (y2 - y1) / 2)
        label = det['label']
        conf = det['conf']
        display_text = f"{label} {conf:.2f}"
        # Draw bounding box and label
        if label == 'person':
            rgb = (0, 255, 0)
        elif label == 'car':
            rgb = (255, 0, 0)
        else:
            rgb = (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), rgb, 2)
        cv2.line(frame, (center_point_x, y1), (center_point_x, y2), rgb, 2)
        cv2.line(frame, (x1, center_point_y), (x2, center_point_y), rgb, 2)
        cv2.putText(frame, display_text, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        # print(f"检测到 {display_text} at ({center_point_x}, {center_point_y})")

def extract_frames_from_rtmp(rtmp_url: str, show_window : bool = True, flight_state: FlightState = None, writer=print):
    """向后兼容的包装函数，内部改用 StreamPredictor。"""
    predictor = StreamPredictor(rtmp_url, show_window=show_window, flight_state=flight_state, writer=writer)
    predictor.run()


if __name__ == "__main__":
    # 直接运行类版本
    extract_frames_from_rtmp(source)
