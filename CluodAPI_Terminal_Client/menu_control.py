class MenuControl:
    def __init__(self):
        self.control_dict = {}

    def add_control(self, key, function, description):
        """添加控制选项"""
        self.control_dict[key] = {
            "function": function,
            "description": description
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
        for key, value in self.control_dict.items():
            if user_input == key:
                value["function"]()
                break
        else:
            print("未知命令，请重试")
        

