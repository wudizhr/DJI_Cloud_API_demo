from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, Input, RichLog, TabbedContent, TabPane, Label
from textual.containers import HorizontalGroup, VerticalGroup
from textual.reactive import reactive

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

    def get_menu_str(self):
        lines = [
            "  a - 请求授权云端控制消息",
            "  j - 进入指令飞行控制模式",
            "  c - 进入键盘控制模式",
            "  f - 杆位解锁无人机",
            "  g - 杆位锁定无人机",
            "  h - 解锁飞机并飞行到指定高度",
            "  e - 重置云台",
            "  r - 相机变焦",
            "  t - 设置直播镜头",
            "  y - 设置直播画质",
            "\n"
            "  d - 开启/关闭信息打印",
            "  o - 开始/结束信息保存",
            "  m - 开启/关闭DRC心跳",
            "  n - 开启/关闭DRC消息打印",
            "  q - 退出程序",
        ]
        return "\n".join(lines)

    def compose(self) -> ComposeResult:
        """Create child widgets of a menu."""
        yield Static("Main Menu")
        yield Static(self.get_menu_str(), classes="menu-print")
        yield RichLog(id="command_log", classes="menu-log", max_lines=100)
        yield Input(placeholder="Enter command here")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Event handler called when input is submitted."""
        command = event.value
        # self.app.query_one("#command_log", RichLog).clear()  # clear previous lines
        self.app.query_one("#command_log", RichLog).write(command)
        event.input.value = ""  # clear the input after submission
        # self.command_prompt = command

    def watch_command_prompt(self, prompt: str) -> None:
        """Called when the command_prompt changes."""
        # Update the placeholder of the Input widget
        input_widget = self.query_one(Input)
        input_widget.placeholder = prompt

class Main_display(HorizontalGroup):
    """The main display widget."""

    def compose(self) -> ComposeResult:
        """Create child widgets of the main display."""
        yield Menu_widget(classes="menu-item")
        yield UAV_tabs()

class UAV_App(App):
    """A Textual app to manage UAVs."""

    CSS_PATH = "vertical_layout.tcss"

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield Main_display()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

if __name__ == "__main__":
    app = UAV_App()
    app.run()