from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, Input, RichLog, TabbedContent, TabPane, Label
from textual.containers import HorizontalGroup, VerticalGroup
from textual.reactive import reactive
from multi_client_mqtt import MAIN_CONTROL_Client
from textual import events

def get_control_menu_str() -> str:
    menu_str = (
        "键盘控制飞行器:\n"
        "w/s: 前后倾 | a/d: 左右倾\n"
        "j/k: 油门升降 | q/e: 左右转\n"
        "up: 解锁起飞 | down: 降落\n"
        "o: 退出键盘控制\n"
        "注意：请保持焦点处于此窗口内\n"
    )
    return menu_str

class UAV_shower(VerticalGroup):
    """A UAV shower widget."""
    UAV_info : str = reactive("No Info")

    def compose(self) -> ComposeResult:
        """Create child widgets of a UAV shower."""
        yield Static("Info")
        yield Label(self.UAV_info, classes="Info-box")
        yield Static("Log")
        yield RichLog(id="uav_log", classes="Log-box")

    def watch_UAV_info(self, info: str) -> None:
        """Called when the UAV_info changes."""
        try:
            # 按类选择器查找更精确，同时捕获未创建时的异常
            info_label = self.query_one(".Info-box", Label)
            info_label.update(info)
        except Exception:
            # 子控件尚未创建，忽略此次更新（稍后再次触发时会生效）
            return

class UAV_tabs(VerticalGroup):
    """A UAV tabs widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets of a UAV tabs."""
        # Each tab pane contains a separate UAV_shower instance
        with TabbedContent():
            with TabPane("UAV1", id="uav1"):
                yield UAV_shower(id="UAV1")
            with TabPane("UAV2", id="uav2"):
                yield UAV_shower(id="UAV2")
            with TabPane("UAV3", id="uav3"):
                yield UAV_shower(id="UAV3")

    def update_info(self) -> None:
        """Update UAV info periodically."""
        for i in range(3):
            uav_shower = self.query_one(f"#UAV{i + 1}", UAV_shower)
            uav_info = self.app.multi_client.clients[i].flight_state.get_uav_info_str()
            uav_shower.UAV_info = uav_info

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.update_timer = self.set_interval(1 / 10, self.update_info)

class Control_Log(RichLog):
    """A control log widget."""
    is_control : bool = False
    stick_value : int = 300

    def on_key(self, event: events.Key) -> None:
        if self.is_control:
            if event.key == "o":
                self.is_control = False
                self.app.query_one("#command_log", RichLog).write("已退出键盘控制模式")
                menu_widget = self.app.query_one(Menu_widget)
                menu_widget.active_menu = self.app.multi_client.menu_now.get_menu_str()
                self.app.query_one(Input).focus()
                return
            multi_client = self.app.multi_client
            if multi_client.uav_select_num == 99:
                for client in multi_client.clients:
                    client.drc_controler.key_control_sender(event.key, self.stick_value)
            else:
                client = multi_client.clients[multi_client.uav_select_num - 1]
                client.drc_controler.key_control_sender(event.key, self.stick_value)


class Menu_widget(VerticalGroup):
    """A menu widget."""

    command_prompt = reactive("Enter command here")
    active_menu : str = reactive("")
    is_change_menu : bool = False
    main_title : str = reactive("无人机控制终端 - 已选择全部无人机")

    def compose(self) -> ComposeResult:
        """Create child widgets of a menu."""
        yield Label("无人机控制终端 - 已选择全部无人机", classes="main-title")
        yield Label("a  -   切换菜单", classes="change-print")
        yield Label("c  -   键盘控制飞行器", classes="change-print")
        yield Control_Log(id="menu_log", classes="menu-print")
        yield RichLog(id="command_log", classes="menu-log", max_lines=100)
        yield Input(placeholder="Enter command here")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Event handler called when input is submitted."""
        command = event.value
        event.input.value = ""
        try:
            if not self.is_change_menu:
                if command == "a":
                    self.app.query_one("#command_log", RichLog).write("请输入无人机编号(1~3),99为全部: ")
                    self.is_change_menu = True
                elif command == "exit":
                    self.app.exit()
                elif command == "clear":
                    self.app.query_one("#command_log", RichLog).clear()
                elif command == "c":
                    menu_log = self.app.query_one("#menu_log", Control_Log)
                    menu_log.is_control = True
                    self.app.query_one("#command_log", RichLog).write(f"键盘控制已开启")
                    self.active_menu = get_control_menu_str()
                    menu_log.focus()
                else:
                    self.app.query_one("#command_log", RichLog).write(command)
                    self.app.multi_client.menu_now.loop_try(command)         
            else:
                self.is_change_menu = False
                uav_id = int(command)
                self.main_title = f"无人机控制终端 - 已选择无人机{uav_id}" if uav_id in [1,2,3] else "无人机控制终端 - 已选择全部无人机"
                self.app.multi_client.change_uav_select_num(command)
                self.active_menu = self.app.multi_client.menu_now.get_menu_str()
                if uav_id in [1,2,3]:
                    self.app.query_one(TabbedContent).active = f"uav{uav_id}"
        except Exception as e:
            self.app.query_one("#command_log", RichLog).write(f"命令执行错误: {e}")


    def watch_command_prompt(self, prompt: str) -> None:
        """Called when the command_prompt changes."""
        # Update the placeholder of the Input widget
        input_widget = self.query_one(Input)
        input_widget.placeholder = prompt

    def watch_active_menu(self, menu_str: str) -> None:
        """Called when the active_menu changes."""
        menu_log = self.query_one(".menu-print", Control_Log)
        menu_log.clear()
        menu_log.write(menu_str)

    def watch_main_title(self, title: str) -> None:
        """Called when the main-title changes."""
        title_static = self.query_one(".main-title", Label)
        title_static.update(title)

class Main_display(HorizontalGroup):
    """The main display widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets of the main display."""
        yield Menu_widget(classes="menu-item")
        yield UAV_tabs()

class UAV_TUI_App(App):
    """A Textual app to manage UAVs."""

    CSS_PATH = "TUI_client.tcss"

    BINDINGS = [("t", "toggle_dark", "Toggle dark mode")]

    multi_client : MAIN_CONTROL_Client

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield Main_display()
        
    def on_mount(self) -> None:
        """界面装配完成后触发，这时可以安全 query_one。"""
        sub_log_list = []
        command_log = self.query_one("#command_log ", RichLog)
        for i in range(3):
            sub_log_list.append(self.query_one(f"#UAV{i + 1}  #uav_log", RichLog))
        self.multi_client = MAIN_CONTROL_Client(3, is_deamon=True, main_log=command_log, sub_log_list=sub_log_list)
        self.multi_client.run()
        self.query_one(Menu_widget).active_menu = self.multi_client.menu_now.get_menu_str()
        self.query_one(Input).focus()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = UAV_TUI_App()
    app.run()
    # print("程序已退出")