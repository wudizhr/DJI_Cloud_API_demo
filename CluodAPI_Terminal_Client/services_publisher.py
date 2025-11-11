import time
import json
import time
from CluodAPI_Terminal_Client.fly_utils import generate_uuid
import threading

OSD_FREQ = 50

# RTMP 直播配置
RTMP_URL = 'rtmp://81.70.222.38:1935/live/Drone001'
VIDEO_INDEX = 'normal-0'  # 视频流索引
VIDEO_QUALITY = 1  # 0=自适应, 1=流畅, 2=标清, 3=高清, 4=超清
video_id = "1581F7FVC257X00D6KZ2/88-0-0/normal-0"


request_cloud_control_authorization_message = {
    "bid": generate_uuid(),
    "data": {
        "control_keys": [
            "flight"
        ],
        "user_callsign": "WUDIZHR",
        "user_id": "123456"
    },
    "method": "cloud_control_auth_request",
    "tid": generate_uuid(),
    "timestamp": 1654070968655
}

enter_live_flight_controls_mode_message = {
    "bid": generate_uuid(),
    "data": {
        "hsi_frequency": 1,
        "mqtt_broker": {
            "address": f"host_addr:1883", # 替换为实际的 MQTT 代理地址
            "client_id": "sn_a",
            "enable_tls": "false",
            "expire_time": 1672744922,
            "password": "jwt_token",
            "username": "sn_a_username"
        },

        "osd_frequency": OSD_FREQ,
    },
    "tid": generate_uuid(),
    "timestamp": 1654070968655,
    "method": "drc_mode_enter"    
}

flyto_message = {
    "bid": generate_uuid(),
    "data": {
        "fly_to_id": generate_uuid(),
        "max_speed": 12,
        "points": [
            {
                "height": 0,
                "latitude": 0,
                "longitude": 0
            }
        ]
    },
    "tid": generate_uuid(),
    "timestamp": 1654070968655,
    "method": "fly_to_point"    
}

return_home_message = {
	"bid": "f9f07aad-d1f1-4dc1-8ad0-a3417fd365cc",
	"data": "null",
	"method": "return_home",
	"tid": "b103b00a-3fcc-476e-9cb6-bc5e27d2defd",
	"timestamp": 1734425015702
}


flyto_dict = {100:"暂未收到返回数据", 101:"取消飞向目标点", 102:"执行失败", 103:"执行成功，已飞向目标点", 104:"执行中"}

class Ser_puberlisher:
    def __init__(self, gateway_sn, client, host_addr, flight_state, time_counter, gateway_sn_code, writer=print, main_writer=print):
        self.gateway_sn = gateway_sn
        self.gateway_sn_code = gateway_sn_code
        self.topic = f"thing/product/{self.gateway_sn}/services"
        self.host_addr = host_addr
        self.client = client
        self.is_print = False
        self.flyto_num = 0
        self.flyto_id = f"flyto_{self.gateway_sn}_{self.flyto_num}"
        self.flyto_reply_flag = 0
        self.flyto_state_code = 100
        self.flight_state = flight_state
        self.flyto_time_counter = time_counter
        self.writer = writer
        self.main_writer = main_writer

    def publish_request_cloud_control_authorization(self):
        request_cloud_control_authorization_message["timestamp"] = int(time.time() * 1000)
        self.client.publish(self.topic, payload=json.dumps(request_cloud_control_authorization_message))
        if self.is_print:
            self.writer(f"✅ 请求云端控制指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_enter_live_flight_controls_mode(self):
        enter_live_flight_controls_mode_message["data"]["mqtt_broker"]["address"] = f"{self.host_addr}:1883"
        enter_live_flight_controls_mode_message["data"]["mqtt_broker"]["client_id"] = f"sn_{self.gateway_sn}"
        enter_live_flight_controls_mode_message["timestamp"] = int(time.time() * 1000)
        self.client.publish(self.topic, payload=json.dumps(enter_live_flight_controls_mode_message))
        if self.is_print:
            self.writer(f"✅ 进入指令飞行控制模式指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_return_home(self):
        return_home_message["bid"] = generate_uuid()
        return_home_message["tid"] = generate_uuid()
        return_home_message["timestamp"] = int(time.time()  * 1000)
        self.client.publish(self.topic, payload=json.dumps(return_home_message))
        if self.is_print:
            self.writer(f"✅ 一键返航指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_start_live(self):
        # video_id 字符串，格式: {aircraft_sn}/{payload_index}/{video_index}
        self.writer(f"{self.flight_state.device_sn}/88-0-0/normal-0")
        request_data = {
            "url": f'rtmp://81.70.222.38:1935/live/Drone00{self.gateway_sn_code + 1}',
            "url_type": 1,  # RTMP
            "video_id": f"{self.flight_state.device_sn}/88-0-0/normal-0",
            "video_quality": VIDEO_QUALITY
        }
        full_request = {
            "bid": generate_uuid(),
            "data": request_data,
            "tid": generate_uuid(),
            "timestamp": int(time.time() * 1000),
            "method": "live_start_push"
        }
        self.client.publish(self.topic, payload=json.dumps(full_request))
        self.writer(f"📤 无人机{self.gateway_sn}发送 MQTT 请求 (live_start_push)")

    def publish_stop_live(self):
        # video_id 字符串，格式: {aircraft_sn}/{payload_index}/{video_index}
        self.writer(video_id)
        request_data = {
            "video_id":f"{self.flight_state.device_sn}/88-0-0/normal-0",
        }
        full_request = {
            "bid": generate_uuid(),
            "data": request_data,
            "tid": generate_uuid(),
            "timestamp": int(time.time() * 1000),
            "method": "live_stop_push"
        }
        self.client.publish(self.topic, payload=json.dumps(full_request))
        self.writer(f"📤 无人机{self.gateway_sn}发送 MQTT 请求 (live_stop_push)")

    def publish_live_set_quality(self, quality_level):
        full_request = {
            "bid": generate_uuid(),
            "data": {
                "video_id": f"{self.flight_state.device_sn}/88-0-0/normal-0",
                "video_quality": quality_level
            },
            "tid": generate_uuid(),
            "timestamp:": int(time.time() * 1000),
            "method": "live_set_quality"
        }
        self.client.publish(self.topic, payload=json.dumps(full_request))
        self.writer(f"📤 无人机{self.gateway_sn}发送 MQTT 请求 (live_set_quality)")

    def publish_flyto_command(self, lat, lon, height):
        height = self.flight_state.takeoff_height + height
        flyto_message["data"]["points"][0]["latitude"] = lat
        flyto_message["data"]["points"][0]["longitude"] = lon
        flyto_message["data"]["points"][0]["height"] = height
        flyto_message["data"]["fly_to_id"] = self.flyto_id
        flyto_message["timestamp"] = int(time.time()  * 1000)
        self.publish_flyto_reset()
        self.client.publish(self.topic, payload=json.dumps(flyto_message))

        if self.is_print:
            self.writer(f"✅ 指点飞行指令已发布到 thing/product/{self.gateway_sn}/services")
        self.writer("="*50)
        self.writer("指点飞行指令详情:")
        self.writer(f"指点飞行指令ID: {self.flyto_id}")
        self.writer(f"目标点坐标: lat={lat}, lon={lon}, height={height}")
        self.writer("正在执行指点飞行指令...")
        last_time = time.time()
        while True:
            now = time.time()
            if self.flyto_reply_flag:
                self.writer("✔ 收到指点飞行指令回复")
                break
            if now - last_time > 10:
                self.writer("❌ 指点飞行指令发送超时，请检查连接是否正常")
                return False
            time.sleep(0.1)
        # 同步
        self.flyto_time_counter.update_now()
        self.flyto_time_counter.update_last()
        if self.flyto_reply_flag == 1:
            self.writer("正在飞往目标点...")
            while True:
                self.writer(f'\r 当前状态: {flyto_dict[self.flyto_state_code]}', end='', flush=True)
                if self.flyto_state_code in [102, 103]:
                    self.writer()
                    self.writer(f"指点飞行结束,执行结果: { flyto_dict[self.flyto_state_code]} ")
                    if self.flyto_state_code == 103:
                        return True
                    else:
                        return False
                if self.flyto_time_counter.get_time_minus() > 10:     
                    self.writer()
                    self.writer("❌ 指点飞行状态更新超时，请检查连接是否正常")
                    return False
                time.sleep(0.1)

    def publish_flyto_list_command(self, pos_list):
        def publish_flyto_list_command_thread():
            self.writer("="*50)
            self.writer(f"无人机{self.gateway_sn}开始执行指点飞行列表...,共{len(pos_list)}个点")
            for pos in pos_list:
                latitude = pos[0]
                longitude = pos[1]
                height = pos[2]
                result = self.publish_flyto_command(latitude, longitude, height)
                self.update_flyto_id()
                if not result:
                    self.writer("指点飞行列表执行中断")
                    return
            self.writer(f"无人机{self.gateway_sn}指点飞行列表执行完毕,共{len(pos_list)}个点")
        thread = threading.Thread(target=publish_flyto_list_command_thread)
        thread.daemon = True
        thread.start()

    def publish_flyto_reset(self):
        self.flyto_reply_flag = 0
        self.flyto_state_code = 100

    def update_flyto_id(self):
        self.flyto_num += 1
        self.flyto_id = f"flyto_{self.gateway_sn}_{self.flyto_num}"

    def set_live_camera_command(self, camera_type):
        message = {
            "data": {
                "video_id": f"{self.flight_state.device_sn}/88-0-0/normal-0",
                "video_type": camera_type
            },
            "timestamp": int(time.time()*100),
            "method": "live_lens_change"
        }
        payload = json.dumps(message)
        self.client.publish(self.topic, payload)

    def connect_to_remoter(self):
        self.publish_request_cloud_control_authorization()
        time.sleep(0.1)
        self.publish_enter_live_flight_controls_mode()
        time.sleep(0.1)

    def command_return_home(self):
        self.publish_return_home()

    def command_start_live(self):
        self.publish_start_live()

    def command_stop_live(self):
        self.publish_stop_live()

    def command_request_cloud_control_authorization(self):
        self.publish_request_cloud_control_authorization()

    def command_enter_live_flight_controls_mode(self):
        self.publish_enter_live_flight_controls_mode()

    def command_set_live_quality(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_writer("请输入直播质量等级(0=自适应, 1=流畅, 2=标清, 3=高清, 4=超清): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                quality_level = int(self.user_input)
                self.publish_live_set_quality(quality_level)
                return 0
        except ValueError:
            self.main_writer("输入错误,请重新输入!")
            return state_count
        
    def command_set_camera(self, user_input, state_count):
        type_dict = {1:"thermal", 2:"wide", 3:"zoom"}
        try:
            if state_count == 0:
                self.main_writer(" 1:红外,2:广角,3:变焦 ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                user_input_num = int(self.user_input)
                self.set_live_camera_command(type_dict[user_input_num])
                return 0
        except ValueError:
            self.main_writer("输入错误,请重新输入!")
            return state_count

        

    