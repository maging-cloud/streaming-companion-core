from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit


class LLMPanel(QWidget):
    def __init__(self, cfg: dict):
        super().__init__()
        layout = QFormLayout(self)
        self._base_url = QLineEdit(cfg.get("base_url", ""))
        self._api_key = QLineEdit(cfg.get("api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._model = QLineEdit(cfg.get("model", ""))
        layout.addRow("Base URL", self._base_url)
        layout.addRow("API Key", self._api_key)
        layout.addRow("Model", self._model)

    def get_config(self) -> dict:
        return {
            "base_url": self._base_url.text().strip(),
            "api_key": self._api_key.text().strip(),
            "model": self._model.text().strip(),
        }
