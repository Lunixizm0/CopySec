from __future__ import annotations

import os

import pystray
from PIL import Image, ImageDraw

ACTIVE_COLOR = (39, 201, 63)
PAUSED_COLOR = (240, 180, 41)


def _icon_image(active: bool) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = ACTIVE_COLOR if active else PAUSED_COLOR
    draw.rounded_rectangle([4, 4, 60, 60], radius=14, fill=color + (255,))
    draw.ellipse([20, 20, 44, 44], outline=(255, 255, 255, 255), width=5)
    return img


class TrayApp:
    def __init__(self, guard, log_dir):
        self.guard = guard
        self.log_dir = log_dir
        self.paused = False
        self.icon = pystray.Icon(
            "CopySec",
            _icon_image(True),
            "CopySec - protection active",
            menu=pystray.Menu(
                pystray.MenuItem(self._toggle_text, self._on_toggle, default=True),
                pystray.MenuItem("Open logs folder", self._on_open_logs),
                pystray.MenuItem("Exit", self._on_quit),
            ),
        )

    def _toggle_text(self, item) -> str:
        return "Resume" if self.paused else "Pause"

    def _on_toggle(self, icon, item) -> None:
        if self.paused:
            self.guard.resume()
            icon.icon = _icon_image(True)
            icon.title = "CopySec - protection active"
        else:
            self.guard.pause()
            icon.icon = _icon_image(False)
            icon.title = "CopySec - protection paused"
        self.paused = not self.paused

    def _on_open_logs(self, icon, item) -> None:
        os.startfile(str(self.log_dir))

    def _on_quit(self, icon, item) -> None:
        self.guard.stop()
        icon.stop()

    def run(self) -> None:
        self.icon.run()
