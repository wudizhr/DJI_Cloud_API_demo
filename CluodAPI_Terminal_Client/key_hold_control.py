#!/usr/bin/env python3
"""
按住 'w' 发送前进（示例打印）并按 'q' 退出的简单脚本。
实现细节：
- 使用低级 stdin（termios/tty/select）读取按键，非阻塞。
- 后台线程以 10Hz 运行：如果最近一次收到 'w' 的时间在阈值内，则打印 "前进"。
- 按 'q' 退出并恢复终端模式。

注意：要使按住生效，终端需要有焦点并且操作系统键盘重复要开启（大多数系统默认开启）。
"""
import sys
import termios
import tty
import select
import threading
import time

FEQUENCY = 20.0  # 20Hz
SEND_INTERVAL = 1.0 / FEQUENCY  
HOLD_THRESHOLD = SEND_INTERVAL  
stick_vlue = 200.0  # 杆量

def ptint_menu():
        print("\n" + "="*50)
        print("🎮 键盘控制无人机菜单:")
        print("  w - 前进")
        print("  a - 左移")
        print("  s - 后退")
        print("  d - 右移")
        print("  q - 左转")
        print("  e - 右转")
        print("  j - 上升")
        print("  k - 下降")
        print("  g - 长按解锁")
        print("  h - 长按降落")
        print("  o - 退出键盘控制")
        print("="*50)

def sender(stop_event, last_w_time_holder, drc_controler, stick_vlue):
    """后台发送线程：每 SEND_INTERVAL 检查是否在按住并发送。"""
    while not stop_event.is_set():
        now = time.time()
        if last_w_time_holder[0] is not None and (now - last_w_time_holder[0]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024 + stick_vlue, 1024, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[1] is not None and (now - last_w_time_holder[1]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024 - stick_vlue, 1024, 1024, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[2] is not None and (now - last_w_time_holder[2]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024 - stick_vlue, 1024, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[3] is not None and (now - last_w_time_holder[3]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024 + stick_vlue, 1024, 1024, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[4] is not None and (now - last_w_time_holder[4]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024, 1024, 1024 - stick_vlue)
            sys.stdout.flush()
        elif last_w_time_holder[5] is not None and (now - last_w_time_holder[5]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024, 1024, 1024 + stick_vlue)
            sys.stdout.flush()
        elif last_w_time_holder[6] is not None and (now - last_w_time_holder[6]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024, 1024 + stick_vlue, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[7] is not None and (now - last_w_time_holder[7]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024, 1024 - stick_vlue, 1024)
            sys.stdout.flush()
        elif last_w_time_holder[8] is not None and (now - last_w_time_holder[8]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1680, 365, 365, 365)
        elif last_w_time_holder[9] is not None and (now - last_w_time_holder[9]) <= HOLD_THRESHOLD:
            drc_controler.send_stick_control_command(1024, 1024, 365, 1024)            
            sys.stdout.flush()
        time.sleep(SEND_INTERVAL)


def key_control(drc_controler):
    global SEND_INTERVAL, HOLD_THRESHOLD

    print("按住 'w' 前进（示例打印），按 'o' 退出")
    print("确保终端有焦点并允许键盘重复")

    ptint_menu()

    user_input = input("请输入频率: ").strip()
    freq = int(user_input)
    SEND_INTERVAL = 1.0 / freq
    HOLD_THRESHOLD = SEND_INTERVAL
    user_input = input("请输入杆量: ").strip()
    stick_vlue = int(user_input)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # 进入 cbreak 模式，能逐字读取
        stop_event = threading.Event()
        last_w_time_holder = [None, None, None, None, None, None, None, None, None, None]  # 使用列表以便在线程间共享
        t = threading.Thread(target=sender, args=(stop_event, last_w_time_holder, drc_controler, stick_vlue), daemon=True)
        t.start()

        while True:
            # 使用 select 等待输入（超时以便循环检查退出条件）
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == 'o':
                    break
                elif ch == 'w':
                    last_w_time_holder[0] = time.time()
                elif ch == 'a':
                    last_w_time_holder[1] = time.time()
                elif ch == 's':
                    last_w_time_holder[2] = time.time()
                elif ch == 'd':
                    last_w_time_holder[3] = time.time()
                elif ch == 'q':
                    last_w_time_holder[4] = time.time()
                elif ch == 'e':
                    last_w_time_holder[5] = time.time()
                elif ch == 'j':
                    last_w_time_holder[6] = time.time()
                elif ch == 'k':
                    last_w_time_holder[7] = time.time()
                elif ch == 'g':
                    last_w_time_holder[8] = time.time()
                elif ch == 'h':
                    last_w_time_holder[9] = time.time()
                elif ch == '\x03':  # Ctrl-C
                    break
            # 否则继续循环，sender 线程会根据 last_w_time_holder 决定是否发送

    finally:
        pass
        stop_event.set()
        t.join(timeout=1.0)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # print("已退出")


