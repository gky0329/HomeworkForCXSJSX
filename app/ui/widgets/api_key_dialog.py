from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt
import os
import yaml


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure API Key")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._setup_ui()
        self._load_existing()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("DeepSeek API Key")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #569CD6;")
        layout.addWidget(title)

        desc = QLabel(
            "Enter your DeepSeek API key to enable AI-powered code execution.\n"
            "Get one at: https://platform.deepseek.com/api_keys"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(desc)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setStyleSheet(
            "QLineEdit { padding: 8px; font-size: 13px; border: 1px solid #3E3E3E; "
            "border-radius: 4px; background-color: #1E1E1E; color: #D4D4D4; }"
        )
        layout.addWidget(self._key_input)

        btn_layout = QHBoxLayout()

        self._show_btn = QPushButton("Show")
        self._show_btn.setCheckable(True)
        self._show_btn.toggled.connect(self._toggle_visibility)
        btn_layout.addWidget(self._show_btn)

        btn_layout.addStretch()

        skip_btn = QPushButton("Skip (Offline)")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(skip_btn)

        save_btn = QPushButton("Save & Continue")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _toggle_visibility(self, checked):
        if checked:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Hide")
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Show")

    def _load_existing(self):
        env_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if env_key:
            self._key_input.setText(env_key)
            return

        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                api_key = cfg.get("llm", {}).get("api_key", "")
                if api_key:
                    self._key_input.setText(api_key)
        except Exception:
            pass

    def _save_and_accept(self):
        key = self._key_input.text().strip()
        if not key:
            self.accept()
            return

        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

            cfg = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}

            if "llm" not in cfg:
                cfg["llm"] = {}
            cfg["llm"]["api_key"] = key

            with open(config_path, "w") as f:
                yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

            os.environ["DEEPSEEK_API_KEY"] = key
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save API key: {e}")


def show_api_key_dialog(parent=None) -> bool:
    dialog = ApiKeyDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
