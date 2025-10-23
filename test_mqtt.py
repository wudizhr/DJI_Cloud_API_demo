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
username = os.environ["USERNAME"]
password = os.environ["PASSWORD"]

SAVE_FLAG = False
save_name = "out/osd_data.json" # 保存文件名
# 用于文件写入的锁，确保并发回调时写文件安全
save_lock = threading.Lock()

class DJIMQTTClient:
    def __init__(self, enable_heartbeat: bool = True):
        self.setup_client()
        self.drc_controler = DRC_controler(gateway_sn, self.client)
        self.ser_puberlisher = Ser_puberlisher(gateway_sn, self.client, host_addr)
        self.enable_heartbeat = enable_heartbeat
    
    def setup_client(self):
        """设置MQTT客户端"""
        self.client = mqtt.Client(paho.mqtt.enums.CallbackAPIVersion.VERSION2, transport="tcp")
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(username, password)
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected with result code " + str(rc))
        client.subscribe(f"thing/product/{gateway_sn}/drc/up")
        client.subscribe(f"thing/product/{gateway_sn}/events")
        client.subscribe(f"thing/product/{gateway_sn}/services_reply")
        # 启动键盘监听
        self.start_keyboard_listener()
    
    def on_publish(self, client, userdata, mid, reason_code, properties):
        """v2.x 版本的发布成功回调 - 5个参数"""
        # print(f"✅ 消息 #{mid} 发布成功 (原因码: {reason_code})")

    def ptint_menu(self):
            print("\n" + "="*50)
            print("🎮 键盘控制菜单:")
            print("  a - 请求授权云端控制消息")
            print("  j - 进入指令飞行控制模式")
            print("  c - 进入键盘控制模式")
            print("  f - 杆位解锁无人机")
            print("  g - 杆位锁定无人机")
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

                    if user_input == 'a':  #请求授权云端控制消息
                        self.ser_puberlisher.publish_request_cloud_control_authorization()

                    elif user_input == 'j':#    进入指令飞行控制模
                        self.ser_puberlisher.publish_enter_live_flight_controls_mode()
            
                    elif user_input == 'f':   #杆位解锁无人机 roll: 1680 pitch: 360 throttle: 360 yaw: 360
                        self.drc_controler.send_timing_control_command(1680, 365, 365, 365, 2, 10)

                    elif user_input == 'g': #控制飞机降落锁定 roll: 1680 pitch: 360 throttle: 360 yaw: 360
                        self.drc_controler.send_timing_control_command(1024, 1024, 365, 1024, 2, 10)

                    elif user_input == 'c':
                        key_control(self.drc_controler)

                    elif user_input == 'h':
                        self.drc_controler.send_timing_control_command(1024, 1024, 1024 + 200, 1024, 3, 10)

                    elif user_input == 'w': #控制飞机前进
                        self.drc_controler.send_timing_control_command(1024, 1024+100, 1024, 1024, 3, 10)

                    elif user_input == 's': #控制飞机后退
                        self.drc_controler.send_timing_control_command(1024, 1024-100, 1024, 1024, 3, 10)

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
                        self.ser_puberlisher.publish_flyto_command(new_lat, new_lon, target_height)

                    elif user_input == 'd': #显示/关闭信息打印
                        global DEBUG_FLAG
                        DEBUG_FLAG = not DEBUG_FLAG
                        print("打印调试信息:", DEBUG_FLAG)
                    
                    elif user_input == 'o': #开始/结束信息保存
                        global SAVE_FLAG
                        SAVE_FLAG = not SAVE_FLAG
                        print("保存信息:", SAVE_FLAG, f"保存位置: {save_name}")

                    elif user_input == 'm': #开始/关闭DRC心跳
                        self.drc_controler.is_beat = not self.drc_controler.is_beat
                        print("DRC心跳是否开启:", self.drc_controler.is_beat)

                    elif user_input == 'n': #开始/关闭DRC信息打印
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
    
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        global lon, lat, DEBUG_FLAG, height, SAVE_FLAG
        global osd_lock, osd_count, osd_window_start
        message = json.loads(msg.payload.decode("utf-8"))
        method = message.get("method", None)
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
            if method == "fly_to_point_progress":
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