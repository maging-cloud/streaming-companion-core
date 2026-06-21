import sys


def build_console_service(cfg):
    """登録された console provider があれば ConsoleService を組み立てて返す。無ければ None。"""
    from companion_core.console_providers import discover_console_providers, build_service
    providers = discover_console_providers()
    if not providers:
        return None
    return build_service(providers[0], cfg)   # MVP: 先頭 provider を採用


def main():
    from PySide6.QtWidgets import QApplication
    from companion_core.config import load_config
    from companion_settings.window import MainWindow

    cfg = load_config()
    svc = build_console_service(cfg)           # provider 有→「ライブ」タブ、無→設定のみ

    app = QApplication(sys.argv)
    win = MainWindow(cfg=cfg, console_service=svc)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
