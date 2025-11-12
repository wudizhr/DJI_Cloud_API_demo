import json
import threading
import time
from CluodAPI_Terminal_Client.key_hold_control import key_control

video_id = "1581F7FVC257X00D6KZ2/88-0-0/normal-0"

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

standard_camera_zoom_message = {
	"data": {
		"camera_type": "zoom",
		"payload_index": "88-0-0", #DJI Matrice 4E Camera
		"zoom_factor": 2
	},
	"method": "drc_camera_focal_length_set",
	"seq": 0
}

class DRC_controler:
    def __init__(self, gateway_sn, client, flight_state, writer=print, main_writer=print):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/drc/down" 
        self.seq = 0
        self.is_print = False
        self.drc_state = False
        self.writer = writer
        self.main_writer = main_writer
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
            self.writer(f"已发送控制命令:seq={self.seq} roll={roll}, pitch={pitch}, throttle={throttle}, yaw={yaw}")

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
            self.writer(f"设定相对高度{height}米,起飞指令执行中...")
            interval = 1.0 / 20
            total_messages = int(1 * 20)
            for _ in range(total_messages):
                self.send_stick_control_command(1680, 365, 365, 365)
                time.sleep(interval)
            last = time.time()
            initial_height = self.flight_state.height 
            self.flight_state.takeoff_height = initial_height
            while self.flight_state.elevation < height:
                now = time.time()
                self.send_stick_control_command(1024, 1024, 1024 + stick_vlaue, 1024)
                if self.flight_state.elevation < height/10 and now - last > 10:
                    self.writer(f"无人机{self.gateway_sn}响应超时,请检查连接状态")
                    break
                time.sleep(interval)
            else:
                self.writer(f"无人机{self.gateway_sn} 已飞行至指定高度,相对起飞高度{self.flight_state.elevation}米")

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

    def send_camera_zoom_command(self, user_input_num):
        """发送云台变焦命令到DRC"""
        message = standard_camera_zoom_message.copy()
        message["seq"] = self.seq
        message["data"]["zoom_factor"] = user_input_num
        payload = json.dumps(message)
        self.client.publish(self.topic, payload)
        self.seq += 1

    def publish_heartbeat(self):
        if self.is_beat:
            heartbeat_msg = {
                "data": {"timestamp": int(time.time()*100)},
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
                    self.writer(f"心跳线程错误: {e}")
                time.sleep(1.0 / self.heart_freq)
        t = threading.Thread(target=heartbeat_loop)
        t.daemon = True
        t.start()

    def command_unlock(self):
        self.send_timing_control_command(1680, 365, 365, 365, 2, 10)

    def command_lock(self):
        self.send_timing_control_command(1024, 1024, 365, 1024, 2, 10)

    def command_key_control(self):
        key_control(self)

    def command_flyto_height(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_writer("请输入指定高度(相对当前): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                self.user_height = float(self.user_input)
                self.main_writer(f"已设定高度: {self.user_height}米")
                self.main_writer("请输入指定油门杆量: ")
                return 2
            elif state_count == 2:
                self.user_input = user_input
                self.user_throttle = float(self.user_input)
                self.send_stick_to_height(self.user_height, self.user_throttle)
                return 0
        except ValueError:
            self.main_writer("输入错误,请重新输入!")
            return state_count

    def command_reset_camera(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_writer(" 0:回中,1:向下,2:偏航回中,3:俯仰向下 ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                user_input_num = int(self.user_input)
                self.send_camera_reset_command(user_input_num)
                return 0
        except ValueError:
            self.main_writer("输入错误,请重新输入!")
            return state_count

    def command_zoom_camera(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_writer("请输入变焦倍数(整数): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                user_input_num = int(self.user_input)
                self.send_camera_zoom_command(user_input_num)
                return 0
        except ValueError:
            self.main_writer("输入错误,请重新输入!")
            return state_count

    def command_change_beat_flag(self):
        self.is_beat = not self.is_beat
        self.main_writer("DRC心跳是否开启:", self.is_beat)

    def command_change_drc_print(self):
        self.is_print = not self.is_print
        self.main_writer("DRC消息是否开启:", self.is_print)  

    def key_control_sender(self, key, stick_value):
        """根据按键发送对应的摇杆控制命令"""
        roll = 1024
        pitch = 1024
        throttle = 1024
        yaw = 1024

        if key == 'w':
            pitch = 1024 - stick_value  # 前倾
        elif key == 's':
            pitch = 1024 + stick_value  # 后倾
        elif key == 'a':
            roll = 1024 - stick_value   # 左倾
        elif key == 'd':
            roll = 1024 + stick_value   # 右倾
        elif key == 'j':
            throttle = 1024 + stick_value  # 油门升高
        elif key == 'k':
            throttle = 1024 - stick_value  # 油门降低
        elif key == 'q':
            yaw = 1024 - stick_value    # 左转
        elif key == 'e':
            yaw = 1024 + stick_value    # 右转
        elif key == 'up':
            roll = 1680
            pitch = 365
            throttle = 365
            yaw = 365
        elif key == 'down':
            throttle = 365
        else:
            return  # 非控制按键，直接返回

        self.send_stick_control_command(roll, pitch, throttle, yaw)


        
