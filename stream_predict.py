from ultralytics import YOLO
import cv2
from fps_counter import FPSCounter
import logging

logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Load a pretrained YOLO11n model
model_normal = YOLO("yolo11s")
model_drone = YOLO("model/air2air_det_db-yolo11s_i512_c2.pt")
# Define path to video file
# source = "/home/zhr/test_video/天台.MP4"
source = "rtmp://192.168.31.69:1935/live/drone001"
fps_counter = FPSCounter()

def extract_frames_from_rtmp(rtmp_url):
    # 创建视频捕获对象
    cap = cv2.VideoCapture(rtmp_url)

    if not cap.isOpened():
        print(f"错误: 无法打开RTMP流 {rtmp_url}")
        return

    print(f"成功连接到RTMP流: {rtmp_url}")
    print("开始提取帧...")

    try:
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                print("无法读取帧或流已结束")
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            cv2.imshow('RTMP Stream', frame)
    except KeyboardInterrupt:
        print("用户中断提取过程")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    extract_frames_from_rtmp(source)


# # Run inference on the source (streaming generator)
# results_normal = model_normal(source, stream=True, classes=[0,2], imgsz=512, verbose=False, vid_stride=1, conf=0.2)  # generator of results_normal objects

# # FPS / timing variables
# fps = 0.0
# alpha = 0.12  # EMA smoothing factor for FPS
# last_frame_time = None

# # Use explicit iterator so we can measure inference time for each next()
# results_iter = iter(results_normal)
# while True:
#     t_start = time.time()
#     try:
#         result = next(results_iter)
#     except StopIteration:
#         break
#     t_after_infer = time.time()
#     infer_ms = (t_after_infer - t_start) * 1000.0

#     # update FPS (instantaneous then smoothed)
#     if last_frame_time is None:
#         inst_fps = 0.0
#     else:
#         dt = t_after_infer - last_frame_time
#         inst_fps = 1.0 / dt if dt > 0 else 0.0
#     if fps == 0.0:
#         fps = inst_fps
#     else:
#         fps = alpha * inst_fps + (1.0 - alpha) * fps
#     last_frame_time = t_after_infer

#     #drone 
#     frame = result.orig_img  # get original frame (numpy array)
#     result_drone = model_drone(frame, imgsz=512, verbose=True, conf=0.8, classes=[0])
#     boxes = result_drone[0].boxes  # get boxes for the frame
#     for box in boxes:
#         cls_id = int(box.cls[0])
#         conf = box.conf[0]
#         x1, y1, x2, y2 = box.xyxy[0]
#         label = model_drone.names[cls_id]
#         display_text = f"{label} {conf:.2f}"

#         # Draw bounding box
#         cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 5)

#         # Put label text above the bounding box
#         cv2.putText(frame, display_text, (int(x1), int(y1)-10),
#                     cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)    

#     # frame = result.orig_img  # get original frame (numpy array)
#     boxes = result.boxes  # get boxes for the frame
#     for box in boxes:
#         cls_id = int(box.cls[0])
#         conf = box.conf[0]
#         x1, y1, x2, y2 = box.xyxy[0]
#         label = model_normal.names[cls_id]
#         display_text = f"{label} {conf:.2f}"

#         # Draw bounding box
#         cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 5)

#         # Put label text above the bounding box
#         cv2.putText(frame, display_text, (int(x1), int(y1)-10),
#                     cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)

#     # Prepare FPS and inference time text
#     info_fps = f"FPS: {fps:.2f}"
#     info_infer = f"Infer: {infer_ms:.1f} ms"

#     # # draw background rectangle for better readability
#     font = cv2.FONT_HERSHEY_SIMPLEX
#     scale = 0.8
#     thickness = 2
#     margin = 6
#     (w1, h1), _ = cv2.getTextSize(info_fps, font, scale, thickness)
#     (w2, h2), _ = cv2.getTextSize(info_infer, font, scale, thickness)
#     rect_w = max(w1, w2) + margin * 2
#     rect_h = h1 + h2 + margin * 3
#     cv2.rectangle(frame, (5, 5), (5 + rect_w, 5 + rect_h), (0, 0, 0), -1)

#     # put texts
#     cv2.putText(frame, info_fps, (10, 10 + h1), font, scale, (0, 255, 0), thickness)
#     cv2.putText(frame, info_infer, (10, 10 + h1 + margin + h2), font, scale, (0, 255, 0), thickness)

#     # Display the frame with detections
#     cv2.imshow("YOLO11n Detection", frame)

#     # Break the loop if 'q' is pressed
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# cv2.destroyAllWindows()

