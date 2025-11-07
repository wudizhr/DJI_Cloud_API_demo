from ultralytics import YOLO
import cv2
from fps_counter import FPSCounter
import logging
import threading
import queue
import time

logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Load a pretrained YOLO11n model
# NOTE: reduce verbose to avoid blocking on logging output
model_normal = YOLO("model/yolo11s")
model_drone = YOLO("model/air2air_det_db-yolo11s_i512_c2.pt")

source = "rtmp://81.70.222.38:1935/live/Drone001"
fps_counter = FPSCounter()
fps_counter.start()

# 推理帧率计数器
inference_fps_counter = FPSCounter()
inference_fps_counter.start()


def _run_inference_on_frame(frame):
    """Run both models on a frame and return a list of detections.

    Each detection is a dict: {'x1','y1','x2','y2','label','conf'}
    """
    detections = []
    try:
        # drone-focused model (higher conf)
        result_drone = model_drone(frame, imgsz=512, verbose=False, conf=0.5, classes=[0])
        for box in result_drone[0].boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            label = model_drone.names.get(cls_id, str(cls_id))
            detections.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "conf": conf})

        # normal model (lower conf, multiple classes)
        results_normal = model_normal(frame, classes=[0, 2], imgsz=512, verbose=False, vid_stride=1, conf=0.3)
        for box in results_normal[0].boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            label = model_normal.names.get(cls_id, str(cls_id))
            detections.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "conf": conf})
    except Exception as e:
        # keep worker robust; log minimal info
        print(f"Inference error: {e}")
    return detections


def inference_worker(frame_queue: queue.Queue, stop_event: threading.Event, out_lock: threading.Lock, shared):
    """Background thread: consume frames and update shared['detections'] with latest results."""
    while not stop_event.is_set():
        try:
            # wait for next frame for up to 0.5s
            frame = frame_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        # Run inference (may take time) and then store results
        detections = _run_inference_on_frame(frame)
        
        # 推理完成后计数
        inference_fps_counter.increment()
        
        with out_lock:
            shared['detections'] = detections
            shared['ts'] = time.time()

        # mark done
        try:
            frame_queue.task_done()
        except Exception:
            pass


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


def extract_frames_from_rtmp(rtmp_url):
    cap = cv2.VideoCapture(rtmp_url)

    if not cap.isOpened():
        print(f"错误: 无法打开RTMP流 {rtmp_url}")
        return

    print(f"成功连接到RTMP流: {rtmp_url}")

    # bounded queue to limit memory and latency; drop frames when busy
    frame_queue = queue.Queue(maxsize=2)
    stop_event = threading.Event()
    out_lock = threading.Lock()
    shared = {"detections": [], "ts": None}

    worker = threading.Thread(target=inference_worker, args=(frame_queue, stop_event, out_lock, shared), daemon=True)
    worker.start()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("无法读取帧或流已结束")
                break

            fps_counter.increment()

            # prepare display frame
            display = frame.copy()

            # draw FPS box
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.8
            thickness = 2
            margin = 6
            info_fps = f"FPS: {fps_counter.get_fps()}"
            info_inference_fps = f"Inference FPS: {inference_fps_counter.get_fps()}"
            
            # 计算两行文本的尺寸
            (w1, h1), _ = cv2.getTextSize(info_fps, font, scale, thickness)
            (w2, h2), _ = cv2.getTextSize(info_inference_fps, font, scale, thickness)
            rect_w = max(w1, w2) + margin * 2
            rect_h = h1 + h2 + margin * 4
            
            # 绘制背景框
            cv2.rectangle(display, (5, 5), (5 + rect_w, 5 + rect_h), (0, 0, 0), -1)
            
            # 绘制两行文本
            cv2.putText(display, info_fps, (10, 10 + h1), font, scale, (0, 255, 0), thickness)
            cv2.putText(display, info_inference_fps, (10, 10 + h1 + h2 + margin), font, scale, (0, 255, 255), thickness)

            # overlay latest detections if available
            with out_lock:
                detections = shared.get('detections', [])
            if detections:
                draw_detections(display, detections)

            # try to enqueue frame for inference without blocking; drop if full
            try:
                # send a smaller copy optionally to speed transfer; here we send full copy
                frame_queue.put_nowait(frame.copy())
            except queue.Full:
                # drop frame to keep latency low
                pass

            cv2.imshow('RTMP Stream', display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("用户中断提取过程")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # signal worker to stop and wait
        stop_event.set()
        try:
            # give worker a moment to finish
            worker.join(timeout=1.0)
        except Exception:
            pass
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    extract_frames_from_rtmp(source)
