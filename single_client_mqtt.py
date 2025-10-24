import os
import json
import time
import threading
import sys
import paho
import paho.mqtt.client as mqtt
from key_hold_control import key_control
from DRC_controler import DRC_controler
from fly_utils import FlightState
from services_publisher import Ser_puberlisher

host_addr = os.environ["HOST_ADDR"]
username = os.environ["USERNAME"]
password = os.environ["PASSWORD"]

gateway_sn = ["9N9CN2J0012CXY","9N9CN8400164WH","9N9CN180011TJN"]

class DJIMQTTClient:
    def __init__(self, gateway_sn_code):
        self.gateway_sn_code = gateway_sn_code
        self.gateway_sn = gateway_sn[gateway_sn_code]
        self.DEBUG_FLAG = False
        self.flight_state = FlightState()
        self.last_time = 0
        self.now_time = 0
        self.SAVE_FLAG = False
        self.save_name = f"out/osd_data_{self.gateway_sn_code}.json" # 保存文件名
        # 用于文件写入的锁，确保并发回调时写文件安全
        self.save_lock = threading.Lock()
        self.setup_client()
        self.drc_controler = DRC_controler(self.gateway_sn, self.client, self.flight_state)
        self.ser_puberlisher = Ser_puberlisher(self.gateway_sn, self.client, host_addr, self.flight_state)
    
    def setup_client(self):
        """设置MQTT客户端"""
        self.client = mqtt.Client(paho.mqtt.enums.CallbackAPIVersion.VERSION2, transport="tcp")
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(f"{username}_{self.gateway_sn_code}", password)
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"UAV {self.gateway_sn_code + 1} connected with result code " + str(rc))
        client.subscribe(f"thing/product/{self.gateway_sn}/drc/up")
        client.subscribe(f"thing/product/{self.gateway_sn}/events")
        client.subscribe(f"thing/product/{self.gateway_sn}/services_reply")
        # 启动键盘监听
        # self.get_keyboard_listener()
    
    def on_publish(self, client, userdata, mid, reason_code, properties):
        """v2.x 版本的发布成功回调 - 5个参数"""

    def ptint_menu(self):
            print("\n" + "="*50)
            print(f"{self.gateway_sn_code + 1}号无人机 {self.gateway_sn} 🎮 键盘控制菜单:")
            print("="*50)
            print("  a - 请求授权云端控制消息")
            print("  j - 进入指令飞行控制模式")
            print("  c - 进入键盘控制模式")
            print("  f - 杆位解锁无人机")
            print("  g - 杆位锁定无人机")
            print("  h - 解锁飞机并飞行到指定高度")
            print("  w - 控制飞机前进3秒")
            print("  s - 控制飞机后退3秒")
            print("  e - 重置云台")
            print("  u - 飞向目标点")
            print("  i - 多目标点飞行")
            print("  d - 开启/关闭信息打印")
            print("  o - 开始/结束信息保存")
            print("  m - 开启/关闭DRC心跳")
            print("  n - 开启/关闭DRC消息打印")
            print("  q - 退出程序")
            print("="*50)
    
    def get_keyboard_listener(self):
        """启动键盘输入监听"""
        def listener():
            end_flag = True
            while end_flag:
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

                    elif user_input == 'h': #解锁飞机并飞行到指定高度
                        user_input = input("请输入指定高度(相对当前): ").strip()
                        user_height = float(user_input)
                        user_input = input("请输入油门杆量: ").strip()
                        user_throttle = float(user_input)
                        self.drc_controler.send_stick_to_height(user_height, user_throttle)

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
                        user_input = input("请输入目标点高度(相对于当前高度): ").strip()
                        target_height = int(user_input)
                        user_input = input("请输入目标点向东移动距离: ").strip()
                        target_east = int(user_input)
                        user_input = input("请输入目标点向北移动距离: ").strip()
                        target_north = int(user_input)
                        self.ser_puberlisher.publish_flyto_command(target_height, target_east, target_north)
                        self.ser_puberlisher.update_flyto_id()

                    elif user_input == 'i': #飞向目标点列表(相对坐标)
                        pos_list = []
                        user_input = input("航点总数").strip()
                        pos_num = int(user_input)
                        for i in range(pos_num):
                            print(f"第 {i+1} 个航点:")
                            user_input = input("请输入目标点高度(相对于当前高度): ").strip()
                            target_height = int(user_input)
                            user_input = input("请输入目标点向东移动距离: ").strip()
                            target_east = int(user_input)
                            user_input = input("请输入目标点向北移动距离: ").strip()
                            target_north = int(user_input)
                            pos_list.append((target_height, target_east, target_north))
                        self.ser_puberlisher.publish_flyto_body_list_command(pos_list)
        
                    elif user_input == 'o': #飞向目标点列表
                        pos_list = []
                        user_input = input("航点总数").strip()
                        pos_num = int(user_input)
                        for i in range(pos_num):
                            print(f"第 {i+1} 个航点:")
                            user_input = input("请输入目标点高度(相对于当前高度): ").strip()
                            target_height = int(user_input)
                            user_input = input("请输入目标点经度: ").strip()
                            target_lon = int(user_input)
                            user_input = input("请输入目标点纬度: ").strip()
                            target_lat = int(user_input)
                            pos_list.append((target_lat, target_lon, target_height))
                        self.ser_puberlisher.publish_flyto_body_list_command(pos_list)

                    elif user_input == 'd': #显示/关闭信息打印
                        self.DEBUG_FLAG = not self.DEBUG_FLAG
                        print("打印调试信息:", self.DEBUG_FLAG)
                    
                    elif user_input == 'o': #开始/结束信息保存
                        self.SAVE_FLAG = not self.SAVE_FLAG
                        print("保存信息:", self.SAVE_FLAG, f"保存位置: {self.save_name}")

                    elif user_input == 'm': #开始/关闭DRC心跳
                        self.drc_controler.is_beat = not self.drc_controler.is_beat
                        print("DRC心跳是否开启:", self.drc_controler.is_beat)

                    elif user_input == 'n': #开始/关闭DRC信息打印
                        self.drc_controler.is_print = not self.drc_controler.is_print
                        print("DRC消息是否开启:", self.drc_controler.is_print)
                    
                    elif user_input == 'q': #退出程序
                        print("退出无人机单体菜单")
                        end_flag = False
                    
                    else:
                        print("未知命令，请重试")
                        
                except KeyboardInterrupt:
                    print("\n程序被用户中断")
                    # self.client.disconnect()
                    sys.exit(0)
                except Exception as e:
                    print(f"输入错误: {e}")
        
        thread = threading.Thread(target=listener)
        thread.daemon = True
        # thread.start()
        return thread
    
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        message = json.loads(msg.payload.decode("utf-8"))
        method = message.get("method", None)
        if msg.topic == f"thing/product/{self.gateway_sn}/drc/up":
            if method == "osd_info_push":
                self.now_time = time.time()
                data = message.get("data", None)
                self.flight_state.lon = data.get("longitude", None)
                self.flight_state.lat = data.get("latitude", None)
                self.flight_state.height = data.get("height", None)
                line = f"🌍 OSD Info - gateway_sn: {self.gateway_sn}, Lat: {self.flight_state.lat}, Lon: {self.flight_state.lon} , height: {self.flight_state.height})"
                if self.DEBUG_FLAG:
                    print(line)
                if self.SAVE_FLAG:
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

            elif method == "drc_drone_state_push":
                data = message.get("data", None)
                self.flight_state.mode_code = data.get("mode_code", None)
                           
        elif msg.topic == f"thing/product/{self.gateway_sn}/services_reply":
            # pprint.pprint(message)
            if method == "fly_to_point":
                result = message.get("data", {}).get("result", -1)
                if result == 0:
                    self.ser_puberlisher.flyto_reply_flag = 1
                    print("✅ 指点飞指令发送成功")
                else:
                    self.ser_puberlisher.flyto_reply_flag = 2
                    print(f"❌ 指点飞行指令发送失败，错误码: {result}")
            elif method == "return_home":
                result = message.get("data", {}).get("result", -1)
                if result == 0:
                    print("✅ 一键返航指令发送成功")
                else:
                    print(f"❌ 一键返航指令发送失败，错误码: {result}")                
        elif msg.topic == f"thing/product/{self.gateway_sn}/events":
            if method == "fly_to_point_progress":
                data = message.get("data", None)
                status = data.get("status", None)
                fly_to_id = data.get("fly_to_id", None)
                if fly_to_id == self.ser_puberlisher.flyto_id:
                    if status == "wayline_cancel":
                        self.ser_puberlisher.flyto_state_code = 101
                    if status == "wayline_failed":
                        self.ser_puberlisher.flyto_state_code = 102
                    if status == "wayline_ok":
                        self.ser_puberlisher.flyto_state_code = 103
                    if status == "wayline_progress":
                        self.ser_puberlisher.flyto_state_code = 104
     
    def run(self):
        """运行客户端"""
        def client_start():
            self.client.connect(host_addr, 1883, 60)
            self.client.loop_forever()
        thread = threading.Thread(target=client_start)
        thread.daemon = False
        thread.start()

# # 运行客户端
# if __name__ == "__main__":
#     client = DJIMQTTClient(2)
#     client.run()