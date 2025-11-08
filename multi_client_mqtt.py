from CluodAPI_Terminal_Client.single_client_mqtt import DJIMQTTClient
import threading
import time
import sys
from CluodAPI_Terminal_Client.fly_utils import get_points_from_txt
from CluodAPI_Terminal_Client.menu_control import MenuControl
from textual.widgets import RichLog


points_list = [None, None, None]

points_list[0] = get_points_from_txt("uav1.txt", 80)
points_list[1] = get_points_from_txt("uav2.txt", 90)
points_list[2] = get_points_from_txt("uav3.txt", 100)

class MAIN_CONTROL_Client:
    def __init__(self, client_num: int, is_deamon: bool = True, main_log: RichLog = None, sub_log_list: list = None):
        self.uav_select_num = 99
        self.client_num = client_num
        self.clients = []
        for i in range(self.client_num):
            client = DJIMQTTClient(i, is_deamon=is_deamon, main_log=main_log, per_log=sub_log_list[i] if sub_log_list else None)
            self.clients.append(client)  
        self.main_log : RichLog = main_log
        self.main_menu = MenuControl(writer=self.main_log.write if self.main_log else print) 
        # Register main_menu controls (pass callables, do not call them here)
        self.main_menu.add_control("b", self.request_cloud_control, "连接三个遥控器")
        self.main_menu.add_control("c", self.request_DRC_control, "三个遥控器进入指令飞行模式")
        self.main_menu.add_control("d", self.DRC_start_live, "发送开启直播请求", is_states=1)
        self.main_menu.add_control("e", self.DRC_stop_live, "发送关闭直播请求", is_states=1)
        self.main_menu.add_control("1", self.mission_1, "原地起飞", is_states=1)
        self.main_menu.add_control("2", self.mission_2, "无人机原地降落", is_states=1)
        self.main_menu.add_control("3", self.mission_3, "返航", is_states=1)
        self.main_menu.add_control("4", self.mission_4, "前往某个指定点", is_states=1)
        self.main_menu.add_control("5", self.mission_5, "执行预设多航点任务1", is_states=1)
        self.main_menu.add_control("6", self.mission_6, "执行预设多航点任务2", is_states=1)
        self.main_menu.add_control("7", self.mission_7, "执行预设多航点任务3", is_states=1)
        self.menu_now = self.main_menu        

    def print_menu(self):
        self.main_log.write(f"\n当前无人机编号: {self.uav_select_num}")
        self.main_log.write("  a - 切换无人机控制菜单")
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
                    self.main_log.write("\n程序被用户中断")
                    self.disconnect()
                    sys.exit(0)
                except Exception as e:
                    self.main_log.write(f"输入错误: {e}")
        
        thread = threading.Thread(target=listener)
        thread.daemon = True
        thread.start()

    def change_uav_select_num(self, user_input: str):
        self.uav_select_num = int(user_input)
        self.main_log.write(f"已选择无人机编号: {self.uav_select_num}")
        if self.uav_select_num in [1,2,3]:
            self.menu_now = self.clients[self.uav_select_num - 1].menu
        elif self.uav_select_num == 99:
            self.menu_now = self.main_menu
        else:
            self.main_log.write("输入编号错误,请重新输入!")
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
        self.main_log.write("退出程序...")
        self.disconnect()
        sys.exit(0)

    def request_cloud_control(self):
        for client in self.clients:
            client.ser_puberlisher.publish_request_cloud_control_authorization()
        self.main_log.write("已向三个遥控器发送云端控制请求指令!")

    def request_DRC_control(self):
        for client in self.clients:
            client.ser_puberlisher.publish_enter_live_flight_controls_mode()
        self.main_log.write("已向三个遥控器发送DRC控制请求指令!")

    def DRC_start_live(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3),99为全部: ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                if id == 99:
                    for client in self.clients:
                        client.ser_puberlisher.publish_start_live()
                else:
                    self.clients[id-1].ser_puberlisher.publish_start_live()    
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count   

    def DRC_stop_live(self, user_input, state_count):
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3),99为全部: ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                if id == 99:
                    for client in self.clients:
                        client.ser_puberlisher.publish_stop_live()
                else:
                    self.clients[id-1].ser_puberlisher.publish_stop_live()    
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count 

    def mission_1(self, user_input, state_count):  #   原地起飞5米任务
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3),99为全部: ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                self.id = int(self.user_input)
                self.main_log.write("请输入起飞高度(相对地面),单位米: ")
                return 2
            elif state_count == 2:
                self.user_input = user_input
                self.user_height = int(self.user_input)
                self.main_log.write("请输入油门杆量(0~600): ")
                return 3
            elif state_count == 3:
                self.user_input = user_input
                self.user_throttle = float(self.user_input)
                if self.id == 99:
                    for client in self.clients:
                        client.drc_controler.send_stick_to_height(self.user_height, self.user_throttle)
                else:
                    self.clients[self.id-1].drc_controler.send_stick_to_height(self.user_height, self.user_throttle)
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

    def mission_2(self, user_input, state_count):  #   原地降落任务
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3),99为全部: ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(user_input)
                if id == 99:
                    for client in self.clients:
                        client.drc_controler.send_land_command()
                else:
                    self.clients[id-1].drc_controler.send_land_command()
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

    def mission_3(self, user_input, state_count):  #   返航任务
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3),99为全部: ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                if id == 99:
                    for client in self.clients:
                        client.ser_puberlisher.publish_return_home()
                else:
                    self.clients[id-1].ser_puberlisher.publish_return_home()
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

    def mission_4(self, user_input, state_count):  #   飞往指定目标点
        try:
            if state_count == 0:  
                self.main_log.write("请输入无人机编号(1~3): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                self.id = int(self.user_input)
                self.main_log.write("\n")
                self.main_log.write("1.	39.0427514	117.7238255")
                self.main_log.write("2.	39.0437973	117.7235937")
                self.main_log.write("3.	39.0450147	117.7237587")
                self.main_log.write("\n")
                self.main_log.write("请选择航点坐标(1,2,3): ")
                return 2
            elif state_count == 2:
                self.user_input = user_input
                point_id = int(self.user_input)   
                lat = points_list[0][point_id-1][0]
                lon = points_list[0][point_id-1][1]
                height = points_list[0][point_id-1][2]
                self.main_log.write(f"已选择航点{point_id},Lat: {lat}, Lon: {lon}, height: {height}")
                self.clients[self.id - 1].ser_puberlisher.publish_flyto_list_command([[lat, lon, height]])
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count     

    def mission_5(self, user_input, state_count):  #   按照航线1飞行
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[0])
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

    def mission_6(self, user_input, state_count):  #   按照航线2飞行
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[1])
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

    def mission_7(self, user_input, state_count):  #   按照航线3飞行
        try:
            if state_count == 0:
                self.main_log.write("请输入无人机编号(1~3): ")
                return 1
            elif state_count == 1:
                self.user_input = user_input
                id = int(self.user_input)
                self.clients[id-1].ser_puberlisher.publish_flyto_list_command(points_list[2])
                return 0
        except ValueError:
            self.main_log.write("输入错误,请重新输入!")
            return state_count

if __name__ == "__main__":
    main_client = MAIN_CONTROL_Client(3, is_deamon=False)
    main_client.run()
    main_client.start_keyboard_listener()
    # main_client.tui.run()
