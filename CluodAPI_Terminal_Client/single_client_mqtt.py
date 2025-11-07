import os
import json
import time
import threading
import multiprocessing
import sys
import paho
import paho.mqtt.client as mqtt
from CluodAPI_Terminal_Client.DRC_controler import DRC_controler
from CluodAPI_Terminal_Client.fly_utils import FlightState, Time_counter
from CluodAPI_Terminal_Client.services_publisher import Ser_puberlisher
from CluodAPI_Terminal_Client.menu_control import MenuControl
from stream_predict import extract_frames_from_rtmp
from textual.widgets import RichLog
from DroneGeoLocator import DroneGeoLocator

host_addr = os.environ["HOST_ADDR"]
username = os.environ["USERNAME"]
password = os.environ["PASSWORD"]

gateway_sn = ["9N9CN2J0012CXY","9N9CN8400164WH","9N9CN180011TJN"]

class DJIMQTTClient:
    def __init__(self, gateway_sn_code: int, is_deamon: bool = True):
        self.is_deamon = is_deamon
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
        self.flyto_time_counter = Time_counter()
        self.drc_controler = DRC_controler(self.gateway_sn, self.client, self.flight_state)
        self.ser_puberlisher = Ser_puberlisher(self.gateway_sn, self.client, host_addr, 
                                               self.flight_state, self.flyto_time_counter, self.gateway_sn_code)
        self.menu = MenuControl()
        # Register menu controls (pass callables, do not call them here)
        self.menu.add_control("x", self.ser_puberlisher.command_request_cloud_control_authorization, "请求授权云端控制消息")
        self.menu.add_control("j", self.ser_puberlisher.command_enter_live_flight_controls_mode, "进入指令飞行控制模式")
        self.menu.add_control("c", self.drc_controler.command_key_control, "键盘控制模式")
        self.menu.add_control("f", self.drc_controler.command_unlock, "杆位解锁无人机")
        self.menu.add_control("g", self.drc_controler.command_lock, "杆位锁定无人机")
        self.menu.add_control("h", self.drc_controler.command_flyto_height, "解锁并飞行到指定高度")
        self.menu.add_control("e", self.drc_controler.command_reset_camera, "重置云台")
        self.menu.add_control("r", self.drc_controler.command_zoom_camera, "相机变焦")
        self.menu.add_control("t", self.drc_controler.command_set_camera, "设置直播镜头")
        self.menu.add_control("y", self.ser_puberlisher.command_set_live_quality, "设置直播画质")
        self.menu.add_control("s", self.command_view_live_stream, "查看直播画面")
        self.menu.add_control("d", self.command_change_debug_flag, "开启/关闭信息打印")
        self.menu.add_control("o", self.command_change_save_flag, "开始/结束信息保存")
        self.menu.add_control("m", self.drc_controler.command_change_beat_flag, "开启/关闭DRC心跳")
        self.menu.add_control("n", self.drc_controler.command_change_drc_print, "开启/关闭DRC消息打印")
        # q - 退出程序: map to a callable that exits
        self.main_log : RichLog = None
        self.per_log : RichLog = None
        self.locator = DroneGeoLocator(
            sensor_width_mm=8.5,      # 典型1/1.5英寸传感器
            sensor_height_mm=6.4,     # 典型1/1.5英寸传感器
            focal_length_mm=168.0,      # 长焦镜头
            image_width_px=8000,      # 4K图像宽度
            image_height_px=6000      # 4K图像高度
        ) 

    def setup_client(self):
        """设置MQTT客户端"""
        self.client = mqtt.Client(paho.mqtt.enums.CallbackAPIVersion.VERSION2, transport="tcp")
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(f"{username}", password)
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"UAV {self.gateway_sn_code + 1} connected with result code " + str(rc))
        client.subscribe(f"thing/product/{self.gateway_sn}/drc/up")
        client.subscribe(f"thing/product/{self.gateway_sn}/events")
        client.subscribe(f"thing/product/{self.gateway_sn}/services_reply")
        client.subscribe(f"sys/product/{self.gateway_sn}/status")
    
    def on_publish(self, client, userdata, mid, reason_code, properties):
        """v2.x 版本的发布成功回调 - 5个参数"""

    def command_change_debug_flag(self):
        self.DEBUG_FLAG = not self.DEBUG_FLAG
        print("打印调试信息:", self.DEBUG_FLAG)   
    
    def command_change_save_flag(self):
        self.SAVE_FLAG = not self.SAVE_FLAG
        print("保存信息:", self.SAVE_FLAG, f"保存位置: {self.save_name}") 

    def command_view_live_stream(self):
        rtmp_url = f"rtmp://81.70.222.38:1935/live/Drone00{self.gateway_sn_code + 1}"
        # Use a separate process to run OpenCV GUI (cv2.imshow) because OpenCV
        # windowing functions are not reliably thread-safe. Running in a new
        # process isolates the GUI event loop and avoids issues when opening
        # windows multiple times.
        try:
            # if there's already a live stream process, avoid starting another
            proc = getattr(self, 'stream_process', None)
            if proc is not None and proc.is_alive():
                print("直播画面已在运行，不能重复开启")
                return

            ctx = multiprocessing.get_context('spawn')
            p = ctx.Process(target=extract_frames_from_rtmp, args=(rtmp_url,))
            p.daemon = True
            p.start()
            self.stream_process = p
            print(f"Started live view process (pid={p.pid})")
        except Exception as e:
            print(f"无法启动直播进程: {e}")

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        message = json.loads(msg.payload.decode("utf-8"))
        method = message.get("method", None)
        if msg.topic == f"sys/product/{self.gateway_sn}/status":
            # print(self.flight_state.device_sn)
            if self.flight_state.device_sn == None:
                if method == "update_topo":
                    data = message.get("data", None)
                    sub_devices = data.get("sub_devices", [])
                    for device in sub_devices:
                        device_sn = device.get("sn", "")
                        self.flight_state.device_sn = device_sn
                        line = f"📡 设备状态更新 - gateway_sn: {self.gateway_sn}, 设备SN: {device_sn}"
                        if self.DEBUG_FLAG:
                            print(line)
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
                        with self.save_lock:
                            with open(self.save_name, 'a', encoding='utf-8') as sf:
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
                self.flyto_time_counter.update_last()
                self.flyto_time_counter.update_now()
                # print(self.flyto_time_counter.get_time_minus())
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
        thread.daemon = self.is_deamon
        thread.start()

# # 运行客户端
# if __name__ == "__main__":
#     client = DJIMQTTClient(2)
#     client.run()