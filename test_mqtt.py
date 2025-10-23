import os
import json
import pprint
import time
import threading
import sys
import argparse
import paho
import paho.mqtt.client as mqtt
from key_hold_control import key_control
from DRC_controler import DRC_controler
from fly_utils import generate_uuid, move_coordinates
from services_publisher import Ser_puberlisher

DEBUG_FLAG = False

# gateway_sn = "9N9CN8400164WH"   #遥控器 2
# gateway_sn = "9N9CN2J0012CXY"   #遥控器 1
gateway_sn = "9N9CN180011TJN"   #遥控器 3

lon = 0
lat = 0
height = 0

# 用于统计 osd_info_push 接收频率的全局变量
osd_lock = threading.Lock()
osd_count = 0
osd_window_start = int(time.time())

host_addr = os.environ["HOST_ADDR"]

SAVE_FLAG = False
save_name = "out/osd_data.json" # 保存文件名
# 用于文件写入的锁，确保并发回调时写文件安全
save_lock = threading.Lock()

class DJIMQTTClient:
    def __init__(self, enable_heartbeat: bool = True):
        self.setup_client()
        self.drc_controler = DRC_controler(gateway_sn, self.client)
        self.ser_puberlisher = Ser_puberlisher(gateway_sn, self.client)
        self.enable_heartbeat = enable_heartbeat
    
    def setup_client(self):
        """设置MQTT客户端"""
        self.client = mqtt.Client(paho.mqtt.enums.CallbackAPIVersion.VERSION2, transport="tcp")
        self.client.on_publish = self.on_publish_v2
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.username_pw_set("dji", "lab605605")
        # self.client.on_publish = self.on_publish
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected with result code " + str(rc))
        client.subscribe(f"thing/product/{gateway_sn}/drc/up")
        client.subscribe(f"thing/product/{gateway_sn}/events")
        client.subscribe(f"thing/product/{gateway_sn}/services_reply")
        # 启动键盘监听
        self.start_keyboard_listener()
        # 启动DRC心跳线程（1Hz）
        if self.enable_heartbeat:
            self.start_heartbeat()
    
    def on_publish_v2(self, client, userdata, mid, reason_code, properties):
        """v2.x 版本的发布成功回调 - 5个参数"""
        # print(f"✅ 消息 #{mid} 发布成功 (原因码: {reason_code})")

    def ptint_menu(self):
            print("\n" + "="*50)
            print("🎮 键盘控制菜单:")
            print("  a - 请求授权云端控制消息")
            print("  j - 进入指令飞行控制模式")
            print("  f - 杆位解锁无人机")
            print("  g - 杆位锁定无人机")
            print("  c - 进入键盘控制模式")
            print("  h - 控制飞机上升3秒")
            print("  w - 控制飞机前进3秒")
            print("  s - 控制飞机后退3秒")
            print("  e - 重置云台")
            print("  u - 飞向目标点")
            print("  d - 开启/关闭信息打印")
            print("  o - 开始/结束信息保存")
            print("  m - 开启/关闭DRC心跳")
            print("  n - 开启/关闭DRC消息打印")
            print("  q - 退出程序")
            print("="*50)
    
    def start_keyboard_listener(self):
        """启动键盘输入监听"""
        def listener():
            while True:
                try:
                    self.ptint_menu()
                    user_input = input("请输入命令: ").strip()

                    if user_input == 'f':   #杆位解锁无人机 roll: 1680 pitch: 360 throttle: 360 yaw: 360
                        def send_stick_control():
                            """发送1秒的摇杆控制消息，频率10Hz"""
                            duration = 1  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            print(f"📤 杆位解锁无人机")
                            print("--"*20)
                            for _ in range(total_messages):
                                self.drc_controler.send_control_command(1680, 365, 365, 365)
                                # 等待指定间隔
                                time.sleep(interval)
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'g': #控制飞机降落锁定 roll: 1680 pitch: 360 throttle: 360 yaw: 360
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 2  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            print("--"*20)
                            for _ in range(total_messages):
                                self.drc_controler.send_control_command(1024, 1024, 365, 1024)
                                time.sleep(interval)
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'c':
                        print("启动键盘按键保持控制模式")
                        key_control(self.drc_controler)

                    elif user_input == 'h':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 3  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            print("--"*20)
                            for _ in range(total_messages):
                                self.drc_controler.send_control_command(1024, 1024, 1024 + 200, 1024)
                                # 等待指定间隔
                                time.sleep(interval)
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'w': #控制飞机前进
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 6  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            print("--"*20)
                            for _ in range(total_messages):
                                self.drc_controler.send_control_command(1024, 1024+100, 1024, 1024)
                                # 等待指定间隔
                                time.sleep(interval)
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 's': #控制飞机后退
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 3  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            print("--"*20)
                            for _ in range(total_messages):
                                self.drc_controler.send_control_command(1024, 1024-100, 1024, 1024)
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'a':  #请求授权云端控制消息
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "control_keys": [
                                    "flight"
                                ],
                                "user_callsign": "ZHR_Test",
                                "user_id": "123456"
                            },
                            "method": "cloud_control_auth_request",
                            "tid": generate_uuid(),
                            "timestamp": 1704038400000
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'j':#    进入指令飞行控制模
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "hsi_frequency": 1,
                                "mqtt_broker": {
                                    "address": f"{host_addr}:1883", # 替换为实际的 MQTT 代理地址
                                    "client_id": "sn_a",
                                    "enable_tls": "false",
                                    "expire_time": 1672744922,
                                    "password": "jwt_token",
                                    "username": "sn_a_username"
                                },

                                "osd_frequency": 30,
                            },
                            "tid": generate_uuid(),
                            "timestamp": 1654070968655,
                            "method": "drc_mode_enter"
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'e': #重置云台
                        print(" 0:回中,1:向下,2:偏航回中,3:俯仰向下 ")
                        user_input = input("请输入重置模式类型: ").strip()
                        user_input_num = int(user_input)
                        self.drc_controler.send_camera_reset_command(user_input_num)

                    elif user_input == 'u': #飞向目标点
                        user_input = input("请输入目标点高度: ").strip()
                        target_height = int(user_input)
                        user_input = input("请输入目标点向东移动距离: ").strip()
                        target_east = int(user_input)
                        user_input = input("请输入目标点向北移动距离: ").strip()
                        target_north = int(user_input)
                        new_lat, new_lon = move_coordinates(lat, lon, target_north, target_east)
                        print(f"原始坐标: ({lat}, {lon})")
                        print(f"移动后坐标: ({new_lat:.6f}, {new_lon:.6f})")
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "fly_to_id": generate_uuid(),
                                "max_speed": 12,
                                "points": [
                                    {
                                        "height": target_height,
                                        "latitude": new_lat,
                                        "longitude": new_lon
                                    }
                                ]
                            },
                            "tid": generate_uuid(),
                            "timestamp": 1654070968655,
                            "method": "fly_to_point"
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'd': #显示/关闭信息打印
                        global DEBUG_FLAG
                        DEBUG_FLAG = not DEBUG_FLAG
                        print("打印调试信息:", DEBUG_FLAG)
                    
                    elif user_input == 'o': #开始/结束信息保存
                        global SAVE_FLAG
                        SAVE_FLAG = not SAVE_FLAG
                        print("保存信息:", SAVE_FLAG, f"保存位置: {save_name}")

                    elif user_input == 'm': #开始/关闭DRC心跳
                        self.enable_heartbeat = not self.enable_heartbeat 
                        print("DRC心跳是否开启:", self.enable_heartbeat)

                    elif user_input == 'n': #开始/关闭DRC心跳
                        self.drc_controler.is_print = not self.drc_controler.is_print
                        print("DRC消息是否开启:", self.drc_controler.is_print)
                    
                    elif user_input == 'q': #退出程序
                        print("退出程序...")
                        self.client.disconnect()
                        sys.exit(0)
                    
                    else:
                        print("未知命令，请重试")
                        
                except KeyboardInterrupt:
                    print("\n程序被用户中断")
                    self.client.disconnect()
                    sys.exit(0)
                except Exception as e:
                    print(f"输入错误: {e}")
        
        thread = threading.Thread(target=listener)
        thread.daemon = True
        thread.start()

    def start_heartbeat(self):
        """启动一个后台线程,每秒向 thing/product/{gateway_sn}/drc/down 发布 heart_beat 消息,seq 递增"""
        def heartbeat_loop():
            while True:
                try:
                    self.ser_puberlisher.publish_heartbeat()
                    time.sleep(1 / self.ser_puberlisher.freq)
                except Exception as e:
                    print(f"心跳线程错误: {e}")
                    time.sleep(1.0)

        t = threading.Thread(target=heartbeat_loop)
        t.daemon = True
        t.start()
    
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        global lon, lat, DEBUG_FLAG, height, SAVE_FLAG
        global osd_lock, osd_count, osd_window_start
        message = json.loads(msg.payload.decode("utf-8"))
        method = message.get("method", None)
        # if DEBUG_FLAG:
        #     print("📨Got msg: " + msg.topic, method)
        if msg.topic == f"thing/product/{gateway_sn}/drc/up":
            if method == "osd_info_push":
                data = message.get("data", None)
                lon = data.get("longitude", None)
                lat = data.get("latitude", None)
                height = data.get("height", None)
                line = f"🌍 OSD Info - Time: {time.time()}, Lat: {lat}, Lon: {lon} , height: {height})"
                if DEBUG_FLAG:
                    print(line)
                if SAVE_FLAG:
                    message_with_timestamp = {
                        "timestamp": time.time(),
                        "data": data
                    }
                    # 将包含时间戳的消息以 JSON 行追加到文件
                    try:
                        with save_lock:
                            with open(save_name, 'a', encoding='utf-8') as sf:
                                sf.write(json.dumps(message_with_timestamp, ensure_ascii=False) + "\n")
                    except Exception as e:
                        # 不要抛出异常以免影响主线程，记录错误到 stderr
                        print(f"❌ 保存 OSD 数据失败: {e}", file=sys.stderr)

                            
        elif msg.topic == f"thing/product/{gateway_sn}/services_reply":
            # pprint.pprint(msg)
            if method == "takeoff_to_point":
                result = message.get("data", {}).get("result", -1)
                if result == 0:
                    print("✅ 一键起飞指令发送成功")
                else:
                    print(f"❌ 一键起飞指令发送失败，错误码: {result}")
        elif msg.topic == f"thing/product/{gateway_sn}/events":
            if method == "takeoff_to_point_progress":
                status = message.get("status", None)
                if status == "wayline_ok":
                    print("一键起飞执行成功,已飞向目标点")
            if method == "fly_to_point_progress":
                # print("收到任务返回消息", method)
                # pprint.pprint(message)
                data = message.get("data", None)
                status = data.get("status", None)
                if status == "wayline_ok":
                    print("指点飞行执行成功,已到达目标点")
     
    
    def run(self):
        """运行客户端"""
        self.client.connect(host_addr, 1883, 60)
        self.client.loop_forever()

# 运行客户端
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DJI MQTT test client")
    parser.add_argument("--heartbeat", dest="heartbeat", nargs='?', const=True, default=True,
                        help="Enable heartbeat thread (default: true). Pass --heartbeat false or --no-heartbeat to disable.")
    parser.add_argument("--no-heartbeat", dest="heartbeat", action='store_false', help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Normalize heartbeat value (allow strings 'false'/'true')
    hb = args.heartbeat
    if isinstance(hb, str):
        hb_low = hb.strip().lower()
        if hb_low in ("false", "0", "no", "n"):
            hb = False
        else:
            hb = True

    client = DJIMQTTClient(enable_heartbeat=bool(hb))
    client.run()