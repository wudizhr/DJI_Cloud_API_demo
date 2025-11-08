class MenuControl:
    def __init__(self, writer=print):
        self.control_dict = {}
        self.last_command = None
        self.state_count = 0
        self.writer = writer

    def add_control(self, key, function, description, is_states=0):
        """添加控制选项"""
        self.control_dict[key] = {
            "function": function,
            "description": description,
            "is_states": is_states
        }

    def print_menu(self):
        """打印控制菜单"""
        print("控制菜单:")
        for key, value in self.control_dict.items():
            print(f"  {key} - {value['description']}")

    def get_menu_str(self):
        """获取控制菜单"""
        lines = []
        for key, value in self.control_dict.items():
            lines.append(f"  {key} - {value['description']}")

        return "\n".join(lines)
    
    def loop_try(self, user_input):
        if self.last_command is not None:
            self.state_count = self.last_command["function"](user_input, self.state_count)
            if self.state_count == 0:
                self.writer(f"指令 {self.last_command['description']} 已发送")
                self.last_command = None
        else:
            for key, value in self.control_dict.items():
                if user_input == key:
                    if value["is_states"] == 0:
                        self.state_count = value["function"]()
                        self.writer(f"指令 {value['description']} 已发送")
                    else:
                        self.state_count = value["function"](user_input, self.state_count)
                        if self.state_count != 0:
                            self.last_command = value
                        else:
                            self.writer(f"指令 {value['description']} 已发送")
                            self.last_command = None
                    break
            else:
                self.writer("未知命令，请重试")
        

