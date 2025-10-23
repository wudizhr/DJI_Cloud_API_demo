import time
import json
import time
from fly_utils import generate_uuid

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

        "osd_frequency": 30,
    },
    "tid": generate_uuid(),
    "timestamp": 1654070968655,
    "method": "drc_mode_enter"    
}

flayto_message = {
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

flyto_dict = {100:"暂未收到返回数据", 101:"取消飞向目标点", 102:"执行失败", 103:"执行成功，已飞向目标点", 104:"执行中"}

class Ser_puberlisher:
    def __init__(self, gateway_sn, client, host_addr):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/services"
        self.host_addr = host_addr
        self.client = client
        self.is_print = False
        self.flyto_num = 0
        self.flyto_id = ""
        self.flyto_reply_flag = 0
        self.flyto_state_code = 100

    def publish_request_cloud_control_authorization(self):
        request_cloud_control_authorization_message["timestamp"] = int(time.time() * 1000)
        self.client.publish(self.topic, payload=json.dumps(request_cloud_control_authorization_message))
        if self.is_print:
            print(f"✅ 请求云端控制指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_enter_live_flight_controls_mode(self):
        enter_live_flight_controls_mode_message["data"]["mqtt_broker"]["address"] = f"{self.host_addr}:1883"
        enter_live_flight_controls_mode_message["timestamp"] = int(time.time() * 1000)
        self.client.publish(self.topic, payload=json.dumps(enter_live_flight_controls_mode_message))
        if self.is_print:
            print(f"✅ 进入指令飞行控制模式指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_flyto_command(self, latitude, longitude, height):
        flayto_message["data"]["points"][0]["latitude"] = latitude
        flayto_message["data"]["points"][0]["longitude"] = longitude
        flayto_message["data"]["points"][0]["height"] = height
        self.flyto_id = f"flyto_{self.gateway_sn}_{self.flyto_num}"
        flayto_message["data"]["fly_to_id"] = self.flyto_id
        flayto_message["timestamp"] = int(time.time()  * 1000)
        self.client.publish(self.topic, payload=json.dumps(flayto_message))
        self.publish_flyto_reset()
        self.flyto_num += 1
        if self.is_print:
            print(f"✅ 指点飞行指令已发布到 thing/product/{self.gateway_sn}/services")
        print("="*50)
        print("指点飞行指令详情:")
        print(f"指点飞行指令ID: {self.flyto_id}")
        print(f"目标点坐标: lat={latitude}, lon={longitude}, height={height}")
        print("正在执行指点飞行指令...")
        last_time = time.time()
        while True:
            now = time.time()
            if self.flyto_reply_flag:
                print("✔ 收到指点飞行指令回复")
                break
            if now - last_time > 10:
                print("❌ 指点飞行指令发送超时，请检查连接是否正常")
                return False
            time.sleep(0.1)
        last_time = time.time()
        if self.flyto_reply_flag == 1:
            print("正在飞往目标点...")
            while True:
                now = time.time()
                print(f'\r 当前状态: {flyto_dict[self.flyto_state_code]}', end='', flush=True)
                if self.flyto_state_code in [102, 103]:
                    print()
                    print(f"指点飞行结束,执行结果: { flyto_dict[self.flyto_state_code]} ")
                    if self.flyto_state_code == 103:
                        return True
                    else:
                        return False
                if now - last_time > 20:     
                    print()
                    print("❌ 指点飞行状态更新超时，请检查连接是否正常")
                    return False
                time.sleep(0.1)

    def publish_flyto_list_command(self, pos_list):
        print("="*50)
        print("开始执行指点飞行列表...")
        for pos in pos_list:
            latitude = pos[0]
            longitude = pos[1]
            height = pos[2]
            result = self.publish_flyto_command(latitude, longitude, height)
            if not result:
                print("指点飞行列表执行中断")
                return
        print(f"指点飞行列表执行完毕,共{len(pos_list)}个点")

    def publish_flyto_reset(self):
        self.flyto_reply_flag = 0
        self.flyto_state_code = 100


    
        

    