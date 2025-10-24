from single_client_mqtt import DJIMQTTClient
import threading
import time
import sys

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
                        print("1")
                        user_input = input("请输入指定高度(相对当前): ").strip()
                        user_height = float(user_input)
                        user_input = input("请输入油门杆量: ").strip()
                        user_throttle = float(user_input)
                        user_input = input("请输入无人机编号: ").strip()
                        id = int(user_input)
                        self.mission_1(user_height, user_throttle, id)

                    elif user_input == '2':
                        print("2")
                    elif user_input == '3':
                        print("3")
                    elif user_input == '4':
                        print("4")
                    elif user_input == '5':
                        print("5")
                    elif user_input == '6':
                        print("6")
                    elif user_input == '7':
                        print("7")
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

if __name__ == "__main__":
    main_client = MAIN_CONTROL_Client(3)
    print(main_client.clients[0].gateway_sn)
    print(main_client.clients[1].gateway_sn)
    print(main_client.clients[2].gateway_sn)
    main_client.run()
    