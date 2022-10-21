from __future__ import annotations

import asyncio
from asyncio import Task
from pathlib import Path

import aiofiles
from rich.markdown import Markdown
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Container
from textual.screen import Screen
from textual.widgets import Static, Footer

from _directory import Directory
from _header import Header
from _preview import Preview


class Home(Screen):
    BINDINGS = [
        Binding("enter", "choose_path", "Go"),
        Binding("g", "top_of_file", "Top"),
        Binding("G", "bottom_of_file", "Bottom"),
        Binding("question_mark", "app.push_screen('help')", "Help", key_display="?"),
        Binding("ctrl+c", "quit", "Exit"),
    ]

    _update_preview_task: Task | None = None

    def compose(self) -> ComposeResult:
        cwd = Path.cwd()
        parent = Directory(path=cwd.parent, id="parent-dir", classes="dir-list")
        parent.can_focus = False
        parent.select_path(cwd)

        yield Header()
        yield Horizontal(
            parent,
            Directory(path=cwd, id="current-dir", classes="dir-list"),
            Container(Preview(id="preview"), id="preview-wrapper"),
        )
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:
        self.query_one("#current-dir").focus(scroll_visible=False)

    def on_directory_file_preview_changed(self, event: Directory.FilePreviewChanged):
        """When we press up or down to highlight different dirs or files, we
        need to update the preview on the right-hand side of the screen."""

        # Ensure the message is coming from the correct directory widget
        # TODO: Could probably add a readonly flag to Directory to prevent having this check
        print(f"FILE PREVIEW CHANGED: {event.path}")
        if event.sender.id == "current-dir":
            if event.path.is_file():
                asyncio.create_task(self.show_syntax(event.path))
            elif event.path.is_dir():
                self.query_one("#preview", Preview).show_directory_preview(event.path)

    def on_directory_current_dir_changed(self, event: Directory.CurrentDirChanged):
        new_directory = event.new_dir
        directory_widget = self.query_one("#current-dir", Directory)
        directory_widget.update_source_directory(new_directory)
        print(f"event.from_dir = {event.from_dir}")
        directory_widget.select_path(event.from_dir)

        parent_directory_widget = self.query_one("#parent-dir", Directory)
        parent_directory_widget.update_source_directory(new_directory.parent)
        parent_directory_widget.select_path(new_directory)

    async def show_syntax(self, path: Path) -> None:
        async with aiofiles.open(path, mode='r') as f:
            # TODO - if they start scrolling preview, load more than 1024 bytes.
            contents = await f.read(2048)
        self.query_one("#preview", Preview).show_syntax(contents, path)


class Help(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Exit Help Screen"),
    ]

    def compose(self) -> ComposeResult:
        help_path = Path(__file__).parent / "kupo_commands.md"
        help_text = help_path.read_text(encoding="utf-8")
        rendered_help = Markdown(help_text)
        yield Static(rendered_help)
        yield Footer()


class Kupo(App):
    CSS_PATH = "kupo.css"
    SCREENS = {
        "home": Home(),
        "help": Help(),
    }
    BINDINGS = []

    def on_mount(self) -> None:
        self.push_screen("home")


app = Kupo()
if __name__ == "__main__":
    app.run()
