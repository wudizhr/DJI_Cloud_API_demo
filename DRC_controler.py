import json
import threading
import time

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
        self.seq = 0
        self.is_print = False
        self.drc_state = False
        #   drc_heartbeat
        self.is_beat = True
        self.heart_freq = 1.0  # 心跳频率，单位Hz
        self.client = client
        self.start_heartbeat()

    def send_stick_control_command(self, roll, pitch, throttle, yaw):
        """发送控制命令到DRC"""
        message = standard_control_message.copy()
        message["seq"] = self.seq
        message["data"]["roll"] = roll
        message["data"]["pitch"] = pitch
        message["data"]["throttle"] = throttle
        message["data"]["yaw"] = yaw
        payload = json.dumps(message)
        self.client.publish(self.topic, payload)
        self.seq += 1
        if self.is_print:
            print(f"已发送控制命令:seq={self.seq} roll={roll}, pitch={pitch}, throttle={throttle}, yaw={yaw}")

    def send_timing_control_command(self, roll, pitch, throttle, yaw, duration, frequency):
        """发送定时控制命令到DRC"""
        interval = 1.0 / frequency
        total_messages = int(duration * frequency)

        def send_commands():
            for _ in range(total_messages):
                self.send_stick_control_command(roll, pitch, throttle, yaw)
                time.sleep(interval)

        thread = threading.Thread(target=send_commands)
        thread.daemon = True
        thread.start()


    def send_camera_reset_command(self, client, user_input_num):
        """发送云台复位命令到DRC"""
        message = standard_camera_message.copy()
        message["seq"] = self.seq
        message["data"]["reset_mode"] = user_input_num
        payload = json.dumps(message)
        client.publish(self.topic, payload)
        self.seq += 1

    def publish_heartbeat(self):
        if self.is_beat:
            heartbeat_msg = {
                "data": {"timestamp": int(time.time() * 1000)},
                "method": "heart_beat",
                "seq": self.seq,
            }
            self.client.publish(self.topic, payload=json.dumps(heartbeat_msg), qos=1)
            self.seq += 1
            # if self.is_print:
            #     print(f"❤️ 心跳已发送: seq={self.seq}")

    def start_heartbeat(self):
        def heartbeat_loop():
            while True:
                try:
                    self.publish_heartbeat()
                except Exception as e:
                    print(f"心跳线程错误: {e}")
                time.sleep(1.0 / self.heart_freq)
        t = threading.Thread(target=heartbeat_loop)
        t.daemon = True
        t.start()




