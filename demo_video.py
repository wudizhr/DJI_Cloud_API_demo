from ultralytics import YOLO
import cv2
import time
import os


source = "drone_video.mp4"
# Load a pretrained YOLO11n model
model = YOLO("model/air2air_det_db-yolo11s_i512_c2.pt", task='detect')

# 检查模型使用的provider
if hasattr(model, 'predictor') and hasattr(model.predictor, 'model'):
    session = model.predictor.model.session
    print("Model is using provider:", session.get_providers())
    print("Current execution provider:", session.get_providers()[0])

# 创建视频输出设置
output_dir = "output_videos"
os.makedirs(output_dir, exist_ok=True)

# 获取输入视频信息
cap = cv2.VideoCapture(source)
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()

print(f"输入视频信息: {width}x{height}, FPS: {fps:.2f}, 总帧数: {total_frames}")

# 创建视频写入器
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(output_dir, f"detection_result_{timestamp}.mp4")

# 定义视频编码器（根据系统选择）
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4格式
# fourcc = cv2.VideoWriter_fourcc(*'XVID')  # AVI格式

out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

results = model(source, stream=True, imgsz=512, max_det=10, conf=0.8)

# FPS / timing variables
processing_fps = 0.0
alpha = 0.12
last_frame_time = None

results_iter = iter(results)
frame_count = 0
detection_count = 0

print("开始处理视频...")

while True:
    t_start = time.time()
    try:
        result = next(results_iter)
    except StopIteration:
        break
    t_after_infer = time.time()
    
    frame_count += 1
    frame = result.orig_img
    boxes = result.boxes
    
    # 添加调试信息
    if frame_count % 30 == 0:  # 每30帧打印一次
        print(f"Frame {frame_count}: {len(boxes) if boxes else 0} detections")
    
    if boxes is not None and len(boxes) > 0:
        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            conf = box.conf[0]
            x1, y1, x2, y2 = box.xyxy[0]
            label = model.names[cls_id]
            
            detection_count += 1
            
            # 绘制边界框
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
            
            # 添加标签背景（增强可读性）
            label_text = f"{label} {conf:.2f}"
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(frame, (int(x1), int(y1)-label_size[1]-10), 
                         (int(x1)+label_size[0], int(y1)), (0, 255, 0), -1)
            
            # 添加标签
            cv2.putText(frame, label_text, (int(x1), int(y1)-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # 计算处理FPS
    infer_ms = (t_after_infer - t_start) * 1000.0

    if last_frame_time is None:
        inst_fps = 0.0
    else:
        dt = t_after_infer - last_frame_time
        inst_fps = 1.0 / dt if dt > 0 else 0.0
    if processing_fps == 0.0:
        processing_fps = inst_fps
    else:
        processing_fps = alpha * inst_fps + (1.0 - alpha) * processing_fps
    last_frame_time = t_after_infer

    # 绘制信息面板
    info_texts = [
        f"FPS: {processing_fps:.2f}",
        f"Infer: {infer_ms:.1f}ms",
        f"Frame: {frame_count}/{total_frames}",
        f"Detections: {detection_count}"
    ]
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    thickness = 2
    margin = 5
    
    # 计算信息面板尺寸
    max_width = 0
    total_height = 0
    for text in info_texts:
        (w, h), _ = cv2.getTextSize(text, font, scale, thickness)
        max_width = max(max_width, w)
        total_height += h + margin
    
    # 绘制背景面板
    panel_x, panel_y = 10, 10
    cv2.rectangle(frame, (panel_x, panel_y), 
                 (panel_x + max_width + margin*2, panel_y + total_height + margin), 
                 (0, 0, 0), -1)
    
    # 绘制文本
    current_y = panel_y + 20
    for text in info_texts:
        cv2.putText(frame, text, (panel_x + margin, current_y), 
                   font, scale, (0, 255, 0), thickness)
        current_y += 20

    # 写入视频帧
    out.write(frame)
    
    # 显示帧（可选）
    cv2.imshow("YOLO Detection - Press 'q' to stop", frame)
    
    # 进度显示
    if frame_count % 10 == 0:
        progress = (frame_count / total_frames) * 100
        print(f"进度: {progress:.1f}% ({frame_count}/{total_frames}) - 处理FPS: {processing_fps:.2f}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("用户中断处理")
        break

# 释放资源
out.release()
cv2.destroyAllWindows()

print(f"\n✅ 视频处理完成!")
print(f"输出文件: {output_path}")
print(f"总帧数: {frame_count}")
print(f"总检测数: {detection_count}")
print(f"平均处理FPS: {processing_fps:.2f}")