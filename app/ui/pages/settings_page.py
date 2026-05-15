from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.app_settings import AppSettings
from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE
from app.ui.widgets.mc_button import McButton


class SettingsPage(QWidget):
    back_requested = Signal()
    settings_changed = Signal(str, str, str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.setStyleSheet(APP_STYLE)
        self._settings = settings
        self._api_url = settings.api_url
        self._api_key = settings.api_key
        self._model = settings.model
        self._last_url_choice = ""
        self._last_model_choice = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("• 设置")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {Colors.CREAM};")

        tip = QLabel("请填写服务地址与 Key（仅保存在本次运行中）")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setStyleSheet(f"font-size: 13px; color: {Colors.MUTED};")

        panel = QWidget()
        panel.setStyleSheet(
            f"background: {Colors.PANEL_BG}; border: 3px solid {Colors.STONE_DARK}; "
            f"border-radius: 4px; padding: 12px;"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(10)

        url_label = QLabel("• URL")
        url_label.setStyleSheet(f"font-size: 14px; color: {Colors.CREAM};")
        self._url_combo = QComboBox()
        self._url_combo.addItems(["https://api.deepseek.com", "其他"])
        self._url_combo.currentTextChanged.connect(self._handle_url_choice)
        self._apply_combo_font(self._url_combo)
        self._url_combo.setStyleSheet("font-size: 14px;")

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("URL 将显示在这里")
        self._url_input.setReadOnly(True)
        self._url_input.setMinimumHeight(36)

        key_label = QLabel("• API Key")
        key_label.setStyleSheet(f"font-size: 14px; color: {Colors.CREAM};")
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("请输入 API Key")
        self._key_input.setMinimumHeight(36)
        self._key_input.textChanged.connect(self._on_key_changed)

        model_label = QLabel("• Model")
        model_label.setStyleSheet(f"font-size: 14px; color: {Colors.CREAM};")
        self._model_combo = QComboBox()
        self._model_combo.addItems(["deepseek-v4-flash", "deepseek-v4-pro", "其他"])
        self._model_combo.currentTextChanged.connect(self._handle_model_choice)
        self._apply_combo_font(self._model_combo)
        self._model_combo.setStyleSheet("font-size: 14px;")

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("Model 将显示在这里")
        self._model_input.setReadOnly(True)
        self._model_input.setMinimumHeight(36)

        panel_layout.addWidget(url_label)
        panel_layout.addWidget(self._url_combo)
        url_row = QHBoxLayout()
        url_row.setContentsMargins(12, 0, 0, 0)
        url_arrow = QLabel("→")
        url_arrow.setStyleSheet(f"font-size: 14px; color: {Colors.MUTED};")
        url_row.addWidget(url_arrow)
        url_row.addWidget(self._url_input)
        panel_layout.addLayout(url_row)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(key_label)
        panel_layout.addWidget(self._key_input)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(model_label)
        panel_layout.addWidget(self._model_combo)
        model_row = QHBoxLayout()
        model_row.setContentsMargins(12, 0, 0, 0)
        model_arrow = QLabel("→")
        model_arrow.setStyleSheet(f"font-size: 14px; color: {Colors.MUTED};")
        model_row.addWidget(model_arrow)
        model_row.addWidget(self._model_input)
        panel_layout.addLayout(model_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        back_btn = McButton("← 返回")
        back_btn.clicked.connect(self.back_requested.emit)
        save_btn = McButton("保存")
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)

        self._save_status = QLabel("")
        self._save_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._save_status.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {Colors.GRASS_LIGHT};"
        )

        layout.addWidget(title)
        layout.addWidget(tip)
        layout.addWidget(panel)
        layout.addStretch()
        layout.addWidget(self._save_status)
        layout.addLayout(btn_row)

        self._sync_initial_state()

    def _handle_url_choice(self, text: str) -> None:
        if text == "https://api.deepseek.com":
            self._api_url = text
            self._url_input.setText(text)
            self._last_url_choice = text
            self._emit_settings()
            return

        custom = self._ask_custom_url()
        if custom:
            self._api_url = custom
            self._url_input.setText(custom)
            self._last_url_choice = text
            self._emit_settings()
        else:
            self._url_combo.blockSignals(True)
            self._url_combo.setCurrentText(self._last_url_choice or "https://api.deepseek.com")
            self._url_combo.blockSignals(False)

    def _handle_model_choice(self, text: str) -> None:
        if text in ("deepseek-v4-flash", "deepseek-v4-pro"):
            self._model = text
            self._model_input.setText(text)
            self._last_model_choice = text
            self._emit_settings()
            return

        custom = self._ask_custom_model()
        if custom:
            self._model = custom
            self._model_input.setText(custom)
            self._last_model_choice = text
            self._emit_settings()
        else:
            self._model_combo.blockSignals(True)
            self._model_combo.setCurrentText(self._last_model_choice or "deepseek-v4-flash")
            self._model_combo.blockSignals(False)

    def _ask_custom_url(self) -> str:
        text, ok = QInputDialog.getText(
            self,
            "输入 URL",
            "请输入服务 URL:",
        )
        return text.strip() if ok else ""

    def _ask_custom_model(self) -> str:
        text, ok = QInputDialog.getText(
            self,
            "输入 Model",
            "请输入模型名称:",
        )
        return text.strip() if ok else ""

    def _on_key_changed(self, text: str) -> None:
        self._api_key = text.strip()

    def _save_settings(self) -> None:
        self._emit_settings()
        self._save_status.setText("✓ API设置已保存！")
        QTimer.singleShot(2000, lambda: self._save_status.setText(""))

    def _emit_settings(self) -> None:
        self._api_key = self._key_input.text().strip()
        self._settings.update(self._api_url, self._api_key, self._model)
        self.settings_changed.emit(self._api_url, self._api_key, self._model)

    def _apply_combo_font(self, combo: QComboBox) -> None:
        font = combo.font()
        if font.pointSize() <= 0:
            font.setPointSize(14)
        combo.setFont(font)
        view = combo.view()
        if view:
            view.setFont(font)
            view.setStyleSheet("font-size: 14px;")

    def _sync_initial_state(self) -> None:
        self._key_input.setText(self._api_key)
        self._url_combo.blockSignals(True)
        self._model_combo.blockSignals(True)

        if self._api_url == "https://api.deepseek.com":
            self._url_combo.setCurrentText("https://api.deepseek.com")
            self._url_input.setText(self._api_url)
            self._last_url_choice = "https://api.deepseek.com"
        else:
            self._url_combo.setCurrentText("其他")
            self._url_input.setText(self._api_url)
            self._last_url_choice = "其他"

        if self._model in ("deepseek-v4-flash", "deepseek-v4-pro"):
            self._model_combo.setCurrentText(self._model)
            self._model_input.setText(self._model)
            self._last_model_choice = self._model
        else:
            self._model_combo.setCurrentText("其他")
            self._model_input.setText(self._model)
            self._last_model_choice = "其他"

        self._url_combo.blockSignals(False)
        self._model_combo.blockSignals(False)
        self._emit_settings()

    def get_api_url(self) -> str:
        return self._api_url

    def get_api_key(self) -> str:
        return self._api_key

    def get_model(self) -> str:
        return self._model
