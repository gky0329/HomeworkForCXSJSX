from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QComboBox, QSpinBox,
)
from PySide6.QtCore import Qt
import logging
import os
import yaml

logger = logging.getLogger(__name__)


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._setup_ui()
        self._load_existing()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #569CD6;")
        layout.addWidget(title)

        desc = QLabel(
            "Configure your DeepSeek API key and connection settings.\n"
            "Get an API key at: https://platform.deepseek.com/api_keys"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(desc)

        input_style = (
            "QLineEdit { padding: 8px; font-size: 13px; border: none; border-bottom: 1px solid #3E3E3E; "
            "background-color: transparent; color: #D4D4D4; }"
            "QLineEdit:focus { border-bottom: 1px solid #007ACC; }"
        )
        combo_style = (
            "QComboBox { padding: 6px 8px; font-size: 13px; border: none; border-bottom: 1px solid #3E3E3E; "
            "background-color: transparent; color: #D4D4D4; } "
            "QComboBox:focus { border-bottom: 1px solid #007ACC; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #1E1E1E; color: #D4D4D4; selection-background-color: #007ACC; }"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(desc)

        input_style = (
            "QLineEdit { padding: 8px; font-size: 13px; border: 1px solid #3E3E3E; "
            "background-color: #1E1E1E; color: #D4D4D4; }"
        )
        label_style = "color: #D4D4D4; font-size: 12px; font-weight: bold; margin-top: 6px;"
        hint_style = "color: #808080; font-size: 11px;"

        api_label = QLabel("API Key")
        api_label.setStyleSheet(label_style)
        layout.addWidget(api_label)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setStyleSheet(input_style)
        layout.addWidget(self._key_input)

        show_layout = QHBoxLayout()
        self._show_btn = QPushButton("Show")
        self._show_btn.setCheckable(True)
        self._show_btn.toggled.connect(self._toggle_visibility)
        show_layout.addWidget(self._show_btn)
        show_layout.addStretch()
        layout.addLayout(show_layout)

        proxy_label = QLabel("Proxy (optional)")
        proxy_label.setStyleSheet(label_style)
        layout.addWidget(proxy_label)

        self._proxy_input = QLineEdit()
        self._proxy_input.setPlaceholderText("e.g. http://127.0.0.1:7890")
        self._proxy_input.setStyleSheet(input_style)
        layout.addWidget(self._proxy_input)

        proxy_hint = QLabel("Leave empty if no proxy. Required for mainland China users to access DeepSeek API.")
        proxy_hint.setWordWrap(True)
        proxy_hint.setStyleSheet(hint_style)
        layout.addWidget(proxy_hint)

        model_label = QLabel("Model")
        model_label.setStyleSheet(label_style)
        layout.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        self._model_combo.setStyleSheet(
            "QComboBox { padding: 6px 8px; font-size: 13px; border: 1px solid #3E3E3E; "
            "background-color: #1E1E1E; color: #D4D4D4; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #1E1E1E; color: #D4D4D4; selection-background-color: #007ACC; }"
        )
        layout.addWidget(self._model_combo)

        model_hint = QLabel("deepseek-chat: fast, good for simple code.  deepseek-reasoner: accurate, better for complex C++.")
        model_hint.setWordWrap(True)
        model_hint.setStyleSheet(hint_style)
        layout.addWidget(model_hint)

        row = QHBoxLayout()
        row.setSpacing(16)

        font_col = QVBoxLayout()
        font_label = QLabel("Code Font Size")
        font_label.setStyleSheet(label_style)
        font_col.addWidget(font_label)
        self._font_spin = QSpinBox()
        self._font_spin.setRange(8, 32)
        self._font_spin.setValue(14)
        self._font_spin.setStyleSheet(input_style.replace("QLineEdit", "QSpinBox"))
        font_col.addWidget(self._font_spin)
        row.addLayout(font_col)
        row.addStretch()
        layout.addLayout(row)

        btn_layout = QHBoxLayout()
        skip_btn = QPushButton("Cancel")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(skip_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("Save")
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
        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                llm_cfg = cfg.get("llm", {})
                ui_cfg = cfg.get("ui", {})

                env_key = os.environ.get("DEEPSEEK_API_KEY", "")
                if env_key:
                    self._key_input.setText(env_key)
                else:
                    api_key = llm_cfg.get("api_key", "")
                    if api_key:
                        self._key_input.setText(api_key)

                proxy = llm_cfg.get("proxy", "")
                if proxy:
                    self._proxy_input.setText(proxy)

                model = llm_cfg.get("model", "deepseek-chat")
                idx = self._model_combo.findText(model)
                if idx >= 0:
                    self._model_combo.setCurrentIndex(idx)

                font_size = ui_cfg.get("code_font_size", 14)
                self._font_spin.setValue(int(font_size))
        except Exception:
            logger.exception("Failed to load existing settings")
            pass

    def _save_and_accept(self):
        key = self._key_input.text().strip()
        proxy = self._proxy_input.text().strip()
        model = self._model_combo.currentText()
        font_size = self._font_spin.value()

        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

            cfg = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}

            if "llm" not in cfg:
                cfg["llm"] = {}
            if key:
                cfg["llm"]["api_key"] = key
            if proxy:
                cfg["llm"]["proxy"] = proxy
            elif "proxy" in cfg["llm"]:
                del cfg["llm"]["proxy"]
            cfg["llm"]["model"] = model

            if "ui" not in cfg:
                cfg["ui"] = {}
            cfg["ui"]["code_font_size"] = font_size

            with open(config_path, "w") as f:
                yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

            if key:
                os.environ["DEEPSEEK_API_KEY"] = key

            if self.parent():
                try:
                    code_editor = self.parent().code_editor
                    current_font = code_editor.font()
                    current_font.setPointSize(font_size)
                    code_editor.setFont(current_font)
                except Exception:
                    pass

            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")


def show_api_key_dialog(parent=None) -> bool:
    dialog = ApiKeyDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
