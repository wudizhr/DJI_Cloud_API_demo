from CluodAPI_Terminal_Client.single_client_mqtt import DJIMQTTClient
import threading
import time
import sys
from CluodAPI_Terminal_Client.fly_utils import get_points_from_txt
from CluodAPI_Terminal_Client.menu_control import MenuControl


points_list = [None, None, None]

points_list[0] = get_points_from_txt("uav1.txt", 80)
points_list[1] = get_points_from_txt("uav2.txt", 90)
points_list[2] = get_points_from_txt("uav3.txt", 100)

class MAIN_CONTROL_Client:
    def __init__(self, client_num: int, is_deamon: bool = True):
        self.uav_select_num = 99
        self.client_num = client_num
        self.clients = []
        for i in range(self.client_num):
            client = DJIMQTTClient(i, is_deamon=is_deamon)
            self.clients.append(client)  
        self.main_menu = MenuControl() 
        # Register main_menu controls (pass callables, do not call them here)
        self.main_menu.add_control("b", self.rquest_cloud_control, "连接三个遥控器")
        self.main_menu.add_control("c", self.rquest_DRC_control, "三个遥控器进入指令飞行模式")
        self.main_menu.add_control("d", self.DRC_start_live, "发送开启直播请求")
        self.main_menu.add_control("e", self.DRC_stop_live, "发送关闭直播请求")
        self.main_menu.add_control("1", self.mission_1, "原地起飞5米")
        self.main_menu.add_control("2", self.mission_2, "无人机原地降落")
        self.main_menu.add_control("3", self.mission_3, "返航")
        self.main_menu.add_control("4", self.mission_4, "前往某个指定点")
        self.main_menu.add_control("5", self.mission_5, "执行预设多航点任务1")
        self.main_menu.add_control("6", self.mission_6, "执行预设多航点任务2")
        self.main_menu.add_control("7", self.mission_7, "执行预设多航点任务3")
        self.menu_now = self.main_menu

    def print_menu(self):
        print(f"\n当前无人机编号: {self.uav_select_num}")
        print("  a - 切换无人机控制菜单")
        self.menu_now.print_menu()

    def start_keyboard_listener(self):
        """启动键盘输入监听"""
        def listener():
            while True:
                try:
                    self.print_menu()
                    user_input = input("请输入命令: ").strip()
                    if user_input == "a":
                        self.change_uav_select_num()
                    else:
                        self.menu_now.loop_try(user_input)
                except KeyboardInterrupt:
                    print("\n程序被用户中断")
                    self.disconnect()
                    sys.exit(0)
                except Exception as e:
                    print(f"输入错误: {e}")
        
        thread = threading.Thread(target=listener)
        thread.daemon = True
        thread.start()

    def change_uav_select_num(self):
        user_input = input("请输入无人机编号(1~3),99为全部: ").strip()
        self.uav_select_num = int(user_input)
        print(f"已选择无人机编号: {self.uav_select_num}")
        if self.uav_select_num in [1,2,3]:
            self.menu_now = self.clients[self.uav_select_num - 1].menu
        elif self.uav_select_num == 99:
            self.menu_now = self.main_menu
        else:
            print("输入编号错误,请重新输入!")
            return
        
    def run(self):
        for client in self.clients:
            client.run()
        time.sleep(0.5)
        # self.start_keyboard_listener()

    def disconnect(self):
        for client in self.clients:
            client.client.disconnect()
    
    def exit_program(self):
        print("退出程序...")
        self.disconnect()
        sys.exit(0)

    def rquest_cloud_control(self):
        for client in self.clients:
            client.ser_puberlisher.publish_request_cloud_control_authorization()
        print("已向三个遥控器发送云端控制请求指令!")

    def rquest_DRC_control(self):
        for client in self.clients:
            client.ser_puberlisher.publish_enter_live_flight_controls_mode()
        print("已向三个遥控器发送DRC控制请求指令!")

    def DRC_start_live(self):
        user_input = input("请输入无人机编号: ").strip()
        id = int(user_input)
        if id == 99:
            for client in self.clients:
                client.ser_puberlisher.publish_start_live()
        else:
            self.clients[id-1].ser_puberlisher.publish_start_live()    

    def DRC_stop_live(self):
        user_input = input("请输入无人机编号: ").strip()
        id = int(user_input)
        if id == 99:
            for client in self.clients:
                client.ser_puberlisher.publish_stop_live()
        else:
            self.clients[id-1].ser_puberlisher.publish_stop_live()    

    def mission_1(self):  #   原地起飞5米任务
        user_input = input("请输入无人机编号: ").strip()
        id = int(user_input)
        user_input = input("请输入指定高度(相对当前): ").strip()
        user_height = float(user_input)
        user_input = input("请输入油门杆量: ").strip()
        user_throttle = float(user_input)
        if id == 99:
            for client in self.clients:
                client.drc_controler.send_stick_to_height(user_height, user_throttle)
        else:
            self.clients[id-1].drc_controler.send_stick_to_height(user_height, user_throttle)

    def mission_2(self):  #   原地降落任务
        user_input = input("请输入无人机编号: ").strip()
        id = int(user_input)
        if id == 99:
            for client in self.clients:
                client.drc_controler.send_land_command()
        else:
            self.clients[id-1].drc_controler.send_land_command()

    def mission_3(self):  #   返航任务
        user_input = input("请输入无人机编号: ").strip()
        id = int(user_input)
        if id == 99:
            for client in self.clients:
                client.ser_puberlisher.publish_return_home()
        else:
            self.clients[id-1].ser_puberlisher.publish_return_home()

    def mission_4(self):  #   飞往指定目标点
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
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command([[lat, lon, height]])       

    def mission_5(self):  #   按照航线1飞行
            user_input = input("请输入无人机编号: ").strip()
            id = int(user_input)
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[0])

    def mission_6(self):  #   按照航线2飞行
            user_input = input("请输入无人机编号: ").strip()
            id = int(user_input)
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[1])

    def mission_7(self):  #   按照航线3飞行
            user_input = input("请输入无人机编号: ").strip()
            id = int(user_input)
            self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[2])

if __name__ == "__main__":
    main_client = MAIN_CONTROL_Client(3, is_deamon=False)
    main_client.run()
    main_client.start_keyboard_listener()
    # main_client.tui.run()
