import os
import json
import pprint
import time
import threading
import sys
from importlib.metadata import version
import paho
import paho.mqtt.client as mqtt
import uuid
import argparse
from geopy.distance import geodesic
from geopy.point import Point

DEBUG_FLAG = False

# gateway_sn = "1581F7FVC257X00D6KZ2" 飞机
# gateway_sn = "9N9CN8400164WH"   #遥控器 2
gateway_sn = "9N9CN2J0012CXY"   #遥控器 1

lon = 0
lat = 0

host_addr = os.environ["HOST_ADDR"]
drc_test_list = [1680, 365]  # roll, pitch, throttle, yaw

def move_coordinates(lat, lon, distance_east, distance_north):
    """
    根据当前经纬度移动指定距离
    
    Args:
        lat: 当前纬度（度）
        lon: 当前经度（度）
        distance_east: 向东移动距离（米），负值表示向西
        distance_north: 向北移动距离（米），负值表示向南
    
    Returns:
        tuple: (新纬度, 新经度)
    """
    # 创建起点
    start = Point(latitude=lat, longitude=lon)
    
    # 先向北移动
    if distance_north != 0:
        bearing_north = 0 if distance_north > 0 else 180
        point_north = geodesic(kilometers=abs(distance_north)/1000).destination(
            start, bearing=bearing_north
        )
    else:
        point_north = start
    
    # 再向东移动
    if distance_east != 0:
        bearing_east = 90 if distance_east > 0 else 270
        final_point = geodesic(kilometers=abs(distance_east)/1000).destination(
            point_north, bearing=bearing_east
        )
    else:
        final_point = point_north
    
    return final_point.latitude, final_point.longitude

def generate_uuid():
    """生成标准UUID格式的随机ID"""
    return str(uuid.uuid4())

class DJIMQTTClient:
    def __init__(self, enable_heartbeat: bool = True):
        self.message_count = 0
        self.setup_client()
        self.drc_seq = 1
        self.heartbeat_seq = 1
        self.enable_heartbeat = enable_heartbeat
    
    def setup_client(self):
        """设置MQTT客户端"""
        PAHO_MAIN_VER = int(version("paho-mqtt").split(".")[0])
        if PAHO_MAIN_VER == 1:
            self.client = mqtt.Client(transport="tcp")
            self.client.on_publish = self.on_publish_v1
        if PAHO_MAIN_VER == 2:
            self.client = mqtt.Client(paho.mqtt.enums.CallbackAPIVersion.VERSION2, transport="tcp")
            self.client.on_publish = self.on_publish_v2
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        # self.client.on_publish = self.on_publish
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected with result code " + str(rc))
        client.subscribe(f"thing/product/{gateway_sn}/drc/up")
        client.subscribe(f"thing/product/{gateway_sn}/events")
        client.subscribe(f"thing/product/{gateway_sn}/services_reply")
        
        # 连接成功后发布欢迎消息
        self.publish_test_message("连接成功欢迎消息")   
        # 启动键盘监听
        self.start_keyboard_listener()
        # 启动DRC心跳线程（1Hz）
        if self.enable_heartbeat:
            self.start_heartbeat()
    

    def on_publish_v1(self, client, userdata, mid):
        """v1.x 版本的发布成功回调 - 3个参数"""
        # print(f"✅ 消息 #{mid} 发布成功")
    
    def on_publish_v2(self, client, userdata, mid, reason_code, properties):
        """v2.x 版本的发布成功回调 - 5个参数"""
        # print(f"✅ 消息 #{mid} 发布成功 (原因码: {reason_code})")
    
    def publish_test_message(self, custom_message=None):
        """发布测试消息到 sys/test"""
        self.message_count += 1
        test_message = {
            "timestamp": int(time.time()),
            "message_id": self.message_count,
            "data": {
                "message": custom_message or f"自动测试消息 #{self.message_count}",
                "source": "dji_cloud_api",
                "version": "1.0"
            }
        }
        
        result = self.client.publish(
            "sys/test", 
            payload=json.dumps(test_message),
            qos=1  # 确保消息送达
        )
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 已发布消息 #{self.message_count} 到 sys/test")
        else:
            print(f"❌ 发布失败，错误码: {result.rc}")

    def ptint_menu(self):
            print("\n" + "="*50)
            print("="*50)
            print("🎮 键盘控制菜单:")
            print("  p - 发布测试消息到 sys/test")
            print("  a - 请求授权云端控制消息")
            print("  j - 进入指令飞行控制模式")
            print("  f - 杆位解锁无人机")
            print("  g - 杆位锁定无人机")
            print("  h - 控制飞机上升3秒")
            print("  w - 控制飞机前进3秒")
            print("  s - 控制飞机后退3秒")
            print("  e - 重置云台")
            print("  r - 云台控制")
            print("  i - 一键起飞")
            print("  u - 飞向目标点")
            print("  t - 测试解锁杆位")
            print("  d - 显示/关闭信息打印")
            print("  q - 退出程序")
            print("="*50)
    
    def start_keyboard_listener(self):
        """启动键盘输入监听"""
        def listener():
            drc_seq = 1
            while True:
                try:
                    self.ptint_menu()
                    user_input = input("请输入命令: ").strip()
                    
                    if user_input == 'p':
                        self.publish_test_message()

                    elif user_input == 'f':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息，频率10Hz"""
                            duration = 1  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            print(f"📤 杆位解锁无人机 ", kind, "roll:", 1680, "pitch:", 
                                    365, "throttle:", 365, "yaw:", 365)
                            print("--"*20)
                            kind += 1
                            for ii in range(total_messages):
                                test_message = {
                                    "seq": self.drc_seq + ii,
                                    "method": "stick_control",
                                    "data": {
                                        "roll": 1680,
                                        "pitch": 365,
                                        "throttle": 365,
                                        "yaw": 365 
                                    }
                                }
                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'g':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 2  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            print(f"📤 控制飞机降落锁定,杆量: ", "roll:", 1024, "pitch:", 
                                    1024, "throttle:", 365, "yaw:", 1024)
                            print("--"*20)
                            kind += 1
                            for ii in range(total_messages):
                                test_message = {
                                    "seq": self.drc_seq + ii,
                                    "method": "stick_control",
                                    "data": {
                                        "roll": 1024,
                                        "pitch": 1024,
                                        "throttle": 365,
                                        "yaw": 1024
                                    }
                                }
                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'h':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 3  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            print(f"📤 控制飞机上升3秒,杆量:200", "roll:", 1024, "pitch:", 
                                    1024, "throttle:", 1024 + 200, "yaw:", 1024)
                            print("--"*20)
                            kind += 1
                            for ii in range(total_messages):
                                test_message = {
                                    "seq": self.drc_seq + ii,
                                    "method": "stick_control",
                                    "data": {
                                        "roll": 1024,
                                        "pitch": 1024,
                                        "throttle": 1024 + 200,
                                        "yaw": 1024
                                    }
                                }
                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'w':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 6  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            print(f"📤 控制飞机前进3秒,杆量:100", "roll:", 1024, "pitch:", 
                                    1024, "throttle:", 1024 + 200, "yaw:", 1024)
                            print("--"*20)
                            kind += 1
                            for ii in range(total_messages):
                                test_message = {
                                    "seq": self.drc_seq + ii,
                                    "method": "stick_control",
                                    "data": {
                                        "roll": 1024,
                                        "pitch": 1024 + 100,
                                        "throttle": 1024,
                                        "yaw": 1024
                                    }
                                }
                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 's':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息,频率10Hz"""
                            duration = 3  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            print(f"📤 控制飞机后退3秒,杆量:100", "roll:", 1024, "pitch:", 
                                    1024, "throttle:", 1024 + 200, "yaw:", 1024)
                            print("--"*20)
                            kind += 1
                            for ii in range(total_messages):
                                test_message = {
                                    "seq": self.drc_seq + ii,
                                    "method": "stick_control",
                                    "data": {
                                        "roll": 1024,
                                        "pitch": 1024 - 100,
                                        "throttle": 1024,
                                        "yaw": 1024
                                    }
                                }
                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                # 等待指定间隔
                                time.sleep(interval)
                            # 更新序列号
                            self.drc_seq += total_messages
                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()
                    
                    elif user_input == 't':
                        def send_stick_control():
                            """发送1秒的摇杆控制消息，频率10Hz"""
                            duration = 1  # 1秒
                            frequency = 10  # 10Hz
                            interval = 1.0 / frequency  # 0.1秒
                            total_messages = int(duration * frequency)  # 10条消息
                            kind = 1
                            # roll: 1680 pitch: 360 throttle: 360 yaw: 360
                            for i in range(2):
                                for j in range(2):
                                    for k in range(2):
                                        for l in range(2):
                                            print(f"📤 测试摇杆控制类型 ", kind, "roll:", drc_test_list[i], "pitch:", 
                                                  drc_test_list[j], "throttle:", drc_test_list[k], "yaw:", drc_test_list[l])
                                            print("--"*20)
                                            kind += 1
                                            for ii in range(total_messages):
                                                test_message = {
                                                    "seq": self.drc_seq + ii,
                                                    "method": "stick_control",
                                                    "data": {
                                                        "roll": drc_test_list[i],
                                                        "pitch": drc_test_list[j],
                                                        "throttle": drc_test_list[k],
                                                        "yaw": drc_test_list[l]
                                                    }
                                                }
                                                self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                                                print(f"📤 发送摇杆控制消息 #{drc_seq + ii}")
                                                # 等待指定间隔
                                                time.sleep(interval)
                                            # 更新序列号
                                            self.drc_seq += total_messages
                                            print(f"✅ 已发送 {total_messages} 条摇杆控制消息，序列号更新为: {self.drc_seq}")
                        # 在新线程中执行，避免阻塞主线程
                        thread = threading.Thread(target=send_stick_control)
                        thread.daemon = True
                        thread.start()

                    elif user_input == 'a':
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "control_keys": [
                                    "flight"
                                ],
                                "user_callsign": "ZHR_Test",
                                "user_id": "123456"
                            },
                            "method": "cloud_control_auth_request",
                            "tid": generate_uuid(),
                            "timestamp": 1704038400000
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'j':
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "hsi_frequency": 1,
                                "mqtt_broker": {
                                    "address": f"{host_addr}:1883", # 替换为实际的 MQTT 代理地址
                                    "client_id": "sn_a",
                                    "enable_tls": "false",
                                    "expire_time": 1672744922,
                                    "password": "jwt_token",
                                    "username": "sn_a_username"
                                },

                                "osd_frequency": 10
                            },
                            "tid": generate_uuid(),
                            "timestamp": 1654070968655,
                            "method": "drc_mode_enter"
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'e':
                        print(" 0:回中,1:向下,2:偏航回中,3:俯仰向下 ")
                        user_input = input("请输入重置模式类型: ").strip()
                        user_input_num = int(user_input)
                        if user_input_num not in [0, 1, 2, 3]:
                            print("无效输入,请输入 0,1,2,3")
                            continue
                        test_message = {
                            "data": {
                                "payload_index": "88-0-0", #DJI Matrice 4E Camera
                                "reset_mode": user_input_num
                            },
                            "method": "drc_gimbal_reset",
                            "seq": self.drc_seq
                        }
                        self.drc_seq += 1
                        self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/drc/down")

                    elif user_input == 'i':
                        user_input = input("请输入目标点高度: ").strip()
                        target_height = int(user_input)
                        user_input = input("请输入指点飞行高度: ").strip()
                        commander_flight_height = int(user_input)
                        user_input = input("请输安全起飞高度: ").strip()
                        security_takeoff_height = int(user_input)
                        user_input = input("请输入目标点向东移动距离: ").strip()
                        target_east = int(user_input)
                        user_input = input("请输入目标点向北移动距离: ").strip()
                        target_north = int(user_input)
                        new_lat, new_lon = move_coordinates(lat, lon, target_north, target_east)
                        print(f"原始坐标: ({lat}, {lon})")
                        print(f"移动后坐标: ({new_lat:.6f}, {new_lon:.6f})")
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "commander_flight_height": commander_flight_height,
                                "commander_mode_lost_action": 1,
                                "flight_id": generate_uuid(),
                                "flight_safety_advance_check": 1,
                                "max_speed": 12,
                                "rc_lost_action": 0,
                                "rth_altitude": 100,
                                "security_takeoff_height": security_takeoff_height,
                                "target_height": target_height,
                                "target_latitude": new_lat,
                                "target_longitude": new_lon
                            },
                            "tid": generate_uuid(),
                            "timestamp": 1654070968655,
                            "method": "takeoff_to_point"
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'u':
                        user_input = input("请输入目标点高度: ").strip()
                        target_height = int(user_input)
                        user_input = input("请输入目标点向东移动距离: ").strip()
                        target_east = int(user_input)
                        user_input = input("请输入目标点向北移动距离: ").strip()
                        target_north = int(user_input)
                        new_lat, new_lon = move_coordinates(lat, lon, target_north, target_east)
                        print(f"原始坐标: ({lat}, {lon})")
                        print(f"移动后坐标: ({new_lat:.6f}, {new_lon:.6f})")
                        test_message = {
                            "bid": generate_uuid(),
                            "data": {
                                "fly_to_id": generate_uuid(),
                                "max_speed": 12,
                                "points": [
                                    {
                                        "height": target_height,
                                        "latitude": new_lat,
                                        "longitude": new_lon
                                    }
                                ]
                            },
                            "tid": generate_uuid(),
                            "timestamp": 1654070968655,
                            "method": "fly_to_point"
                        }
                        self.client.publish(f"thing/product/{gateway_sn}/services", payload=json.dumps(test_message))
                        print(f"✅ 测试消息已发布到 thing/product/{gateway_sn}/services")

                    elif user_input == 'd':
                        global DEBUG_FLAG
                        DEBUG_FLAG = not DEBUG_FLAG
                        print("打印调试信息:", DEBUG_FLAG)
                    
                    elif user_input == 'q':
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

    def start_heartbeat(self):
        """启动一个后台线程,每秒向 thing/product/{gateway_sn}/drc/down 发布 heart_beat 消息,seq 递增"""
        def heartbeat_loop():
            while True:
                try:
                    heartbeat_msg = {
                        "data": {"timestamp": int(time.time() * 1000)},
                        "method": "heart_beat",
                        "seq": self.heartbeat_seq,
                    }
                    # 发布到 DRC down 话题
                    self.client.publish(f"thing/product/{gateway_sn}/drc/down", payload=json.dumps(heartbeat_msg), qos=1)
                    # print(f"💓 已发布 heart_beat seq={self.heartbeat_seq} 到 thing/product/{gateway_sn}/drc/down")
                    self.heartbeat_seq += 1
                    time.sleep(1.0)
                except Exception as e:
                    print(f"心跳线程错误: {e}")
                    # 若发生异常，短暂等待后重试，避免 tight loop
                    time.sleep(1.0)

        t = threading.Thread(target=heartbeat_loop)
        t.daemon = True
        t.start()
    
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        global lon, lat, DEBUG_FLAG
        message = json.loads(msg.payload.decode("utf-8"))
        method = message.get("method", None)
        data = message.get("data", None)
        # if DEBUG_FLAG:
        #     print("📨Got msg: " + msg.topic, method)
        if msg.topic == f"thing/product/{gateway_sn}/drc/up":
            if method == "osd_info_push":
                lon = data.get("longitude", None)
                lat = data.get("latitude", None)
                if DEBUG_FLAG:
                    print(f"🌍 OSD Info - Lat: {lat}, Lon: {lon}") 
        elif msg.topic == f"thing/product/{gateway_sn}/services_reply":
            if method == "takeoff_to_point":
                result = message.get("data", {}).get("result", -1)
                if result == 0:
                    print("✅ 一键起飞指令发送成功")
                else:
                    print(f"❌ 一键起飞指令发送失败，错误码: {result}")
        elif msg.topic == f"thing/product/{gateway_sn}/events":
            if method == "takeoff_to_point_progress":
                status = message.get("status", None)
                if status == "wayline_ok":
                    print("一键起飞执行成功,已飞向目标点")
            if method == "fly_to_point_progress":
                status = message.get("status", None)
                if status == "wayline_ok":
                    print("指点飞行执行成功,已飞向目标点")
     
    
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