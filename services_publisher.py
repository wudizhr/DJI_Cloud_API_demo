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
    "timestamp": time.time()
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

class Ser_puberlisher:
    def __init__(self, gateway_sn, client, host_addr):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/services"
        self.host_addr = host_addr
        self.client = client
        self.is_print = False

    def publish_request_cloud_control_authorization(self):
        self.client.publish(self.topic, payload=json.dumps(request_cloud_control_authorization_message))
        if self.is_print:
            print(f"✅ 请求云端控制指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_enter_live_flight_controls_mode(self):
        enter_live_flight_controls_mode_message["data"]["mqtt_broker"]["address"] = f"{self.host_addr}:1883"
        self.client.publish(self.topic, payload=json.dumps(enter_live_flight_controls_mode_message))
        if self.is_print:
            print(f"✅ 进入指令飞行控制模式指令已发布到 thing/product/{self.gateway_sn}/services")

    def publish_flyto_command(self, latitude, longitude, height):
        flayto_message["data"]["points"][0]["latitude"] = latitude
        flayto_message["data"]["points"][0]["longitude"] = longitude
        flayto_message["data"]["points"][0]["height"] = height
        self.client.publish(self.topic, payload=json.dumps(flayto_message))
        if self.is_print:
            print(f"✅ 飞往坐标指令已发布到 thing/product/{self.gateway_sn}/services")


    
        

    