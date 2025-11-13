"""简单的 RTMP 读取与显示脚本。

功能特性:
1. 指定 RTMP/HTTP/本地流地址 (--url)
2. 自动重连 (--reconnect, --max-retries, --retry-interval)
3. 显示实时 FPS (采集与显示)
4. 可选保存到文件 (--save out.flv / --record-dir 目录分段保存)
5. 支持无窗口模式 (--headless) 仅统计与测试可用性
6. 超时与空帧处理 (--open-timeout, --read-timeout)

使用示例:
	python show_rtmp.py --url rtmp://81.70.222.38:1935/live/Drone001
	python show_rtmp.py --url rtmp://x/live/stream --reconnect --max-retries 5
	python show_rtmp.py --url rtmp://x/live/stream --save out.mp4

退出: 窗口按 'q' 或 Ctrl+C。
"""

from __future__ import annotations
import cv2
import time
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
	from fps_counter import FPSCounter
except Exception:
	# 允许独立运行
	class FPSCounter:
		def __init__(self):
			self.frame_count = 0
			self.fps = 0
			self._last = time.time()
		def start(self):
			self._last = time.time(); self.frame_count = 0; self.fps = 0
		def increment(self):
			self.frame_count += 1
			now = time.time()
			if now - self._last >= 1.0:
				self.fps = self.frame_count; self.frame_count = 0; self._last = now
		def get_fps(self):
			return self.fps


def parse_args(argv=None):
	p = argparse.ArgumentParser(description="RTMP/视频流显示工具")
	# 默认 URL 设置为用户指定的 Drone003
	p.add_argument("--url", default="rtmp://81.70.222.38:1935/live/Drone001", help="RTMP/HTTP/HLS/本地文件路径 (默认: Drone003)")
	p.add_argument("--reconnect", action="store_true", help="断流后自动重连")
	p.add_argument("--max-retries", type=int, default=0, help="最大重连次数(0=无限)")
	p.add_argument("--retry-interval", type=float, default=3.0, help="重连间隔秒数")
	p.add_argument("--open-timeout", type=float, default=10.0, help="首次打开流的最大等待秒数")
	p.add_argument("--read-timeout", type=float, default=10.0, help="连续无法读取帧的最大秒数")
	p.add_argument("--headless", action="store_true", help="不弹出窗口，仅消耗与统计")
	p.add_argument("--save", type=str, default=None, help="保存到单一文件 (根据输入格式自动编码)")
	p.add_argument("--record-dir", type=str, default=None, help="分段保存到目录 (每 N 秒一个文件) 未实现占位")
	p.add_argument("--segment-seconds", type=int, default=0, help="分段保存长度(秒) 0=禁用")
	p.add_argument("--print-every", type=int, default=60, help="每 N 帧打印一次信息")
	return p.parse_args(argv)


class StreamRecorder:
	"""可选的帧保存器。"""
	def __init__(self, path: str, fps: int = 25, width: int = 0, height: int = 0):
		self.path = path
		self.fps = fps
		self.width = width
		self.height = height
		self.writer = None

	def _init_writer(self):
		fourcc = cv2.VideoWriter_fourcc(*"mp4v") if self.path.lower().endswith(".mp4") else cv2.VideoWriter_fourcc(*"XVID")
		self.writer = cv2.VideoWriter(self.path, fourcc, float(self.fps), (self.width, self.height))
		if not self.writer.isOpened():
			raise RuntimeError(f"无法打开输出文件写入: {self.path}")

	def write(self, frame):
		if self.writer is None:
			h, w = frame.shape[:2]
			if not self.width or not self.height:
				self.width, self.height = w, h
			self._init_writer()
		self.writer.write(frame)

	def close(self):
		if self.writer:
			self.writer.release()
			self.writer = None


def open_capture(url: str, timeout: float) -> Optional[cv2.VideoCapture]:
	start = time.time()
	cap = cv2.VideoCapture(url)
	while not cap.isOpened():
		if time.time() - start > timeout:
			cap.release()
			return None
		time.sleep(0.5)
		cap = cv2.VideoCapture(url)
	return cap


def run_stream(args):
	cap = open_capture(args.url, args.open_timeout)
	if cap is None:
		print(f"[error] 打开流失败: {args.url}")
		return 2

	fps_counter = FPSCounter(); fps_counter.start()
	last_read_ok = time.time()
	frame_idx = 0

	recorder = None
	if args.save:
		try:
			recorder = StreamRecorder(args.save)
			print(f"[info] 将保存帧到: {args.save}")
		except Exception as e:
			print(f"[warn] 初始化保存器失败: {e}")
			recorder = None

	window_name = "RTMP Preview"
	if not args.headless:
		# 推迟 resize 到拿到首帧后
		cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

	retry_count = 0
	while True:
		ret, frame = cap.read()
		now = time.time()
		if not ret or frame is None:
			# 读取失败逻辑
			if now - last_read_ok > args.read_timeout:
				print(f"[warn] {args.read_timeout}s 未读取到帧，尝试重连...")
				cap.release()
				if args.reconnect:
					retry_count += 1
					if args.max_retries and retry_count > args.max_retries:
						print("[error] 达到最大重连次数，退出。")
						break
					time.sleep(args.retry_interval)
					cap = open_capture(args.url, args.open_timeout)
					if cap is None:
						print("[error] 重连失败，退出。")
						break
					last_read_ok = time.time()
					continue
				else:
					print("[error] 流读取失败且未开启重连，退出。")
					break
			time.sleep(0.02)
			continue

		last_read_ok = now
		frame_idx += 1
		fps_counter.increment()

		if recorder:
			try:
				recorder.write(frame)
			except Exception as e:
				print(f"[warn] 写帧失败: {e}")

		if not args.headless:
			# 仅首次帧按原分辨率调整窗口大小
			if frame_idx == 1:
				h, w = frame.shape[:2]
				try:
					cv2.resizeWindow(window_name, w, h)
				except Exception:
					pass
			# 叠加 FPS 文本
			display = frame.copy()
			txt = f"FPS: {fps_counter.get_fps()}"
			cv2.putText(display, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
			cv2.imshow(window_name, display)
			key = cv2.waitKey(1) & 0xFF
			if key == ord('q'):
				print("[info] 用户退出")
				break

		# if frame_idx % max(1, args.print_every) == 0:
		# 	print(f"[info] 帧:{frame_idx} FPS:{fps_counter.get_fps()} size:{frame.shape[1]}x{frame.shape[0]}")

	cap.release()
	if recorder:
		recorder.close()
	if not args.headless:
		try:
			cv2.destroyAllWindows()
		except Exception:
			pass
	return 0


def main(argv=None):
	args = parse_args(argv)
	code = run_stream(args)
	sys.exit(code)


if __name__ == "__main__":
	main()

