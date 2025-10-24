from single_client_mqtt import DJIMQTTClient
import threading
import time
import sys
from fly_utils import get_points_from_txt

points_list = [None, None, None]

points_list[0] = get_points_from_txt("uav1.txt", 80)
points_list[1] = get_points_from_txt("uav2.txt", 80)
points_list[2] = get_points_from_txt("uav3.txt", 80)

# print(len(points_list[0]))
class MAIN_CONTROL_Client:
    def __init__(self, client_num):
        self.client_num = client_num
        self.clients = []
        for i in range(self.client_num):
            client = DJIMQTTClient(i)
            self.clients.append(client)   

    def ptint_menu(self):
            print("\n" + "="*50)
            print("🎮 键盘控制菜单:")
            print("  a - 进入指定无人机控制菜单")
            print("  b - 连接三个遥控器")
            print("  q - 退出程序")
            print("="*50)
            print("Mission Control")
            print("="*50)
            print("  1 - 原地起飞5米")
            print("  2 - 无人机原地降落")
            print("  3 - 返航")
            print("  4 - 前往某个指定点")
            print("  5 - 执行预设多航点任务1")
            print("  6 - 执行预设多航点任务2")
            print("  7 - 执行预设多航点任务3")
            print("="*50)

    def start_keyboard_listener(self):
        """启动键盘输入监听"""
        def listener():
            while True:
                try:
                    self.ptint_menu()
                    user_input = input("请输入命令: ").strip()

                    if user_input == 'a': 
                        user_input = input("请选择要进入的无人机编号: ").strip()
                        enter_num = int(user_input) - 1
                        keylistener = self.clients[enter_num].get_keyboard_listener()
                        keylistener.start()
                        while keylistener.is_alive():
                            pass

                    elif user_input == 'b': 
                        self.rquest_cloud_control()

                    elif user_input == '1': 
                        user_input = input("请输入指定高度(相对当前): ").strip()
                        user_height = float(user_input)
                        user_input = input("请输入油门杆量: ").strip()
                        user_throttle = float(user_input)
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_1(user_height, user_throttle, id)

                    elif user_input == '2':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_2(id)

                    elif user_input == '3':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_3(id)

                    elif user_input == '4':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        print("=" * 50)
                        print("1.	39.0427514	117.7238255")
                        print("2.	39.0437973	117.7235937")
                        print("3.	39.0450147	117.7237587")
                        print("=" * 50)
                        user_input = input("请选择航点坐标(1,2,3): ").strip()
                        point_id = int(user_input)   
                        lat = points_list[0][point_id-1][0]
                        lon = points_list[0][point_id-1][1]
                        height = points_list[0][point_id-1][2]
                        print(f"已选择航点{point_id},Lat: {lat}, Lon: {lon}, height: {height}")                     
                        self.mission_4(id, lat, lon, height)

                    elif user_input == '5':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_5(id)
                    elif user_input == '6':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_6(id)
                    elif user_input == '7':
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_7(id)
                    elif user_input == 'q': #退出程序
                        print("退出程序...")
                        self.disconnect()
                        sys.exit(0)
                    else:
                        print("未知命令，请重试")
                        
                except KeyboardInterrupt:
                    print("\n程序被用户中断")
                    self.disconnect()
                    sys.exit(0)
                except Exception as e:
                    print(f"输入错误: {e}")
        
        thread = threading.Thread(target=listener)
        thread.daemon = True
        thread.start()

    def run(self):
        for client in self.clients:
            client.run()
        time.sleep(0.5)
        self.start_keyboard_listener()

    def disconnect(self):
        for client in self.clients:
            client.client.disconnect()

    def rquest_cloud_control(self):
        for client in self.clients:
            client.ser_puberlisher.connect_to_remoter()

    def mission_1(self, height, stick_value, id):  #   原地起飞5米任务
        if id == 99:
            for client in self.clients:
                client.drc_controler.send_stick_to_height(height, stick_value)
        else:
            self.clients[id-1].drc_controler.send_stick_to_height(height, stick_value)

    def mission_2(self, id):  #   原地降落任务
        if id == 99:
            for client in self.clients:
                client.drc_controler.send_land_command()
        else:
            self.clients[id-1].drc_controler.send_land_command()

    def mission_3(self, id):  #   返航任务
        if id == 99:
            for client in self.clients:
                client.ser_puberlisher.publish_return_home()
        else:
            self.clients[id-1].ser_puberlisher.publish_return_home()

    def mission_4(self, id, lat, lon, height):
        if id == 99:
            for client in self.clients:
                client.ser_puberlisher.publish_flyto_command(lat, lon, height)
        else:
            self.clients[id-1].ser_puberlisher.publish_flyto_command(lat, lon, height)       

    def mission_5(self, id):
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[0])    

    def mission_6(self, id):
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[1])    

    def mission_7(self, id):
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[2])         

if __name__ == "__main__":
    main_client = MAIN_CONTROL_Client(3)
    main_client.run()
