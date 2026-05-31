import sys


def main():
    from PySide6.QtWidgets import QApplication
    from companion_settings.window import MainWindow
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
