from __future__ import annotations

import sys

from PySide6 import QtWidgets

from app.env import load_dotenv_if_available
from app.providers import ProviderRegistry
from app.session_manager import SessionManager
from app.ui.main_window import MainWindow


def main() -> None:
    load_dotenv_if_available()
    app = QtWidgets.QApplication(sys.argv)
    registry = ProviderRegistry()
    session_manager = SessionManager()
    restored = session_manager.restore_last()
    if restored:
        session_manager.session = restored
    window = MainWindow(registry, session_manager)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
