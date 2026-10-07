"""Application entry point for VoiceStudio_CF."""

from __future__ import annotations

import sys
from pathlib import Path


APP_ICON = Path(__file__).with_name("assets") / "app_icon.png"
if not APP_ICON.exists():
    APP_ICON = Path(__file__).with_name("assets") / "omni.png"


def _set_windows_app_id() -> None:
    """Thiết lập AppUserModelID cho thanh tác vụ Windows."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CF.VoiceStudio.Desktop"
        )
    except Exception:
        pass


def main() -> int:
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise SystemExit(
            "VoiceStudio_CF yêu cầu PySide6. Hãy cài bằng: pip install PySide6"
        ) from exc

    from .main_window import MainWindow
    from .styles import APP_STYLESHEET

    _set_windows_app_id()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("VoiceStudio_CF")
    app.setOrganizationName("CF")

    if APP_ICON.exists():
        icon = QIcon(str(APP_ICON))
        app.setWindowIcon(icon)

    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    if APP_ICON.exists():
        window.setWindowIcon(QIcon(str(APP_ICON)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
