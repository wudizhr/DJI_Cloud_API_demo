import json

standard_control_message = {
    "seq": 0,
    "method": "stick_control",
    "data": {
        "roll": 1024,
        "pitch": 1024,
        "throttle": 1024,
        "yaw": 1024
    }
}

standard_camera_message = {
    "data": {
        "payload_index": "88-0-0", #DJI Matrice 4E Camera
        "reset_mode": 0
    },
    "method": "drc_gimbal_reset",
    "seq": 0
}

class DRC_controler:
    def __init__(self, gateway_sn, client):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/drc/down" 
        self.drc_state = False
        self.seq = 0
        self.is_print = False
        self.client = client

    def send_control_command(self, roll, pitch, throttle, yaw):
        """发送控制命令到DRC"""
        self.seq += 1
        message = standard_control_message.copy()
        message["seq"] = self.seq
        message["data"]["roll"] = roll
        message["data"]["pitch"] = pitch
        message["data"]["throttle"] = throttle
        message["data"]["yaw"] = yaw
        payload = json.dumps(message)
        self.client.publish(self.topic, payload)
        if self.is_print:
            print(f"已发送控制命令:seq={self.seq} roll={roll}, pitch={pitch}, throttle={throttle}, yaw={yaw}")

    def send_camera_reset_command(self, client, user_input_num):
        """发送云台复位命令到DRC"""
        self.seq += 1
        message = standard_camera_message.copy()
        message["seq"] = self.seq
        message["data"]["reset_mode"] = user_input_num
        payload = json.dumps(message)
        client.publish(self.topic, payload)



