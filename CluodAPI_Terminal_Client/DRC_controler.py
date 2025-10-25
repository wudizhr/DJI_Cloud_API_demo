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
    def __init__(self, gateway_sn, client, flight_state):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/drc/down" 
        self.seq = 0
        self.is_print = False
        self.drc_state = False
        #   drc_heartbeat
        self.is_beat = True
        self.heart_freq = 1.0  # 心跳频率，单位Hz
        self.client = client
        self.flight_state = flight_state
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

    def send_stick_to_height(self, height, stick_vlaue):
        """控制飞机解锁并起飞至指定高度(相对高度)"""
        def send_commands():
            print(f"设定相对高度{height}米,起飞指令执行中...")
            interval = 1.0 / 20
            total_messages = int(1 * 20)
            for _ in range(total_messages):
                self.send_stick_control_command(1680, 365, 365, 365)
                time.sleep(interval)
            last = time.time()
            initial_height = self.flight_state.height 
            self.flight_state.takeoff_height = initial_height
            while self.flight_state.height - initial_height < height:
                now = time.time()
                self.send_stick_control_command(1024, 1024, 1024 + stick_vlaue, 1024)
                if self.flight_state.height - initial_height < height/10 and now - last > 10:
                    print(f"无人机{self.gateway_sn}响应超时,请检查连接状态")
                    break
                time.sleep(interval)
            else:
                print(f"无人机{self.gateway_sn} 已飞行至指定高度,相对高度{self.flight_state.height - initial_height}米")

        thread = threading.Thread(target=send_commands)
        thread.daemon = True
        thread.start()
        
    def send_land_command(self):
        def send_commands():
            limit_time = 30
            last_time = time.time()
            while True:
                self.send_stick_control_command(1024, 1024, 365, 1024)
                now_time = time.time()
                if now_time - last_time > limit_time:
                    (f"无人机{self.gateway_sn}降落超时,请检查连接状态")
                    break
                if self.flight_state.mode_code == 0:
                    (f"无人机{self.gateway_sn}降落成功,正在待机")
                    break
                time.sleep(0.1)

        thread = threading.Thread(target=send_commands)
        thread.daemon = True
        thread.start()


    def send_camera_reset_command(self, user_input_num):
        """发送云台复位命令到DRC"""
        message = standard_camera_message.copy()
        message["seq"] = self.seq
        message["data"]["reset_mode"] = user_input_num
        payload = json.dumps(message)
        self.client.publish(self.topic, payload)
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




