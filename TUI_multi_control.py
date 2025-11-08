from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, Input, RichLog, TabbedContent, TabPane, Label
from textual.containers import HorizontalGroup, VerticalGroup
from textual.reactive import reactive
from multi_client_mqtt import MAIN_CONTROL_Client

class UAV_shower(VerticalGroup):
    """A UAV shower widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets of a UAV shower."""
        yield Static("Info")
        yield Label("Some Info", classes="Info-box")
        yield Static("Log")
        yield RichLog(id="uav_log", classes="Log-box")

class UAV_tabs(VerticalGroup):
    """A UAV tabs widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets of a UAV tabs."""
        # Each tab pane contains a separate UAV_shower instance
        with TabbedContent():
            with TabPane("UAV1"):
                yield UAV_shower(id="UAV1")
            with TabPane("UAV2"):
                yield UAV_shower(id="UAV2")
            with TabPane("UAV3"):
                yield UAV_shower(id="UAV3")

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
        yield Label("", classes="menu-print")
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
                    self.app.multi_client.stop_all_clients()
                    self.app.exit()
                elif command == "clear":
                    self.app.query_one("#command_log", RichLog).clear()
                else:
                    self.app.query_one("#command_log", RichLog).write(command)
                    self.app.multi_client.menu_now.loop_try(command)         
            else:
                self.is_change_menu = False
                uav_id = int(command)
                self.main_title = f"无人机控制终端 - 已选择无人机{uav_id}" if uav_id in [1,2,3] else "无人机控制终端 - 已选择全部无人机"
                self.app.multi_client.change_uav_select_num(command)
                self.active_menu = self.app.multi_client.menu_now.get_menu_str()
        except Exception as e:
            self.app.query_one("#command_log", RichLog).write(f"命令执行错误: {e}")


    def watch_command_prompt(self, prompt: str) -> None:
        """Called when the command_prompt changes."""
        # Update the placeholder of the Input widget
        input_widget = self.query_one(Input)
        input_widget.placeholder = prompt

    def watch_active_menu(self, menu_str: str) -> None:
        """Called when the active_menu changes."""
        menu_label = self.query_one(".menu-print", Label)
        menu_label.update(menu_str)

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

    CSS_PATH = "vertical_layout.tcss"

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

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

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = UAV_TUI_App()
    app.run()
    # print("程序已退出")