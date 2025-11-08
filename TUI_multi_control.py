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

    def compose(self) -> ComposeResult:
        """Create child widgets of a menu."""
        yield Static("Control Menu")
        yield Label("a  -   切换菜单", classes="change-print")
        yield Label("", classes="menu-print")
        yield RichLog(id="command_log", classes="menu-log", max_lines=100)
        yield Input(placeholder="Enter command here")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Event handler called when input is submitted."""
        command = event.value
        self.app.query_one("#command_log", RichLog).write(command)
        event.input.value = ""  # clear the input after submission
        self.app.multi_client.menu_now.loop_try(command)

    def watch_command_prompt(self, prompt: str) -> None:
        """Called when the command_prompt changes."""
        # Update the placeholder of the Input widget
        input_widget = self.query_one(Input)
        input_widget.placeholder = prompt

    def watch_active_menu(self, menu_str: str) -> None:
        """Called when the active_menu changes."""
        menu_label = self.query_one(".menu-print", Label)
        menu_label.update(menu_str)

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
        self.multi_client = MAIN_CONTROL_Client(3, is_deamon=True)
        command_log = self.query_one("#command_log ", RichLog)
        for i in range(3):
            self.multi_client.clients[i].main_log = command_log
            self.multi_client.clients[i].per_log = command_log = self.query_one(f"#UAV{i + 1}  #uav_log", RichLog)
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