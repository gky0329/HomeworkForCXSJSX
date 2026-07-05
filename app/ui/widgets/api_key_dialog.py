import logging
import os
from pathlib import Path

import yaml
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from app.services.ai_service import DEFAULT_PROVIDERS
from app.services.i18n import LANGUAGE_LABELS, get_language, load_language, tr
from app.ui.theme.manager import THEME_LABELS, normalize_theme

logger = logging.getLogger(__name__)

PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "openai": "OpenAI",
    "anthropic": "Claude",
    "gemini": "Gemini",
}


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None, config_path: Path | None = None):
        super().__init__(parent)
        self._config_path = config_path or Path(__file__).parent.parent.parent.parent / "config.yaml"
        self._config = self._load_config()
        load_language(self._config_path)

        llm_cfg = self._config.get("llm", {})
        self._provider = str(llm_cfg.get("provider", "deepseek")).lower()
        if self._provider not in DEFAULT_PROVIDERS:
            self._provider = "deepseek"

        self.setWindowTitle(tr("AI Settings"))
        self.setMinimumSize(640, 520)
        self.setModal(True)
        self._setup_ui()
        self._load_provider_fields(self._provider)
        self._fit_to_screen()

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            return {}
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            logger.exception("Failed to load config")
            return {}

    def _provider_config(self, provider: str) -> dict:
        llm_cfg = self._config.get("llm", {})
        cfg = dict(DEFAULT_PROVIDERS[provider])
        providers = llm_cfg.get("providers", {})
        if isinstance(providers, dict):
            cfg.update(providers.get(provider, {}) or {})

        if provider == "deepseek":
            for key in ("api_base", "api_key", "model"):
                if llm_cfg.get(key):
                    cfg[key] = llm_cfg[key]
        return cfg

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(12)

        title = QLabel(tr("AI Settings"))
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")
        layout.addWidget(tabs, 1)

        ai_page, ai_form = self._tab_page()
        ui_page, ui_form = self._tab_page()
        advanced_page, advanced_form = self._tab_page()

        tabs.addTab(ai_page, tr("AI"))
        tabs.addTab(ui_page, tr("Interface"))
        tabs.addTab(advanced_page, tr("Advanced"))

        self._provider_combo = QComboBox()
        for provider in DEFAULT_PROVIDERS:
            self._provider_combo.addItem(PROVIDER_LABELS.get(provider, provider), provider)
        provider_index = self._provider_combo.findData(self._provider)
        if provider_index >= 0:
            self._provider_combo.setCurrentIndex(provider_index)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._add_labeled_widget(ai_form, tr("Provider"), self._provider_combo)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("model")
        self._add_labeled_widget(ai_form, tr("Model"), self._model_input)

        self._base_input = QLineEdit()
        self._base_input.setPlaceholderText("https://...")
        self._add_labeled_widget(ai_form, tr("API Base"), self._base_input)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText(tr("API Key"))
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)

        key_row = QWidget()
        show_layout = QHBoxLayout(key_row)
        show_layout.setContentsMargins(0, 0, 0, 0)
        show_layout.setSpacing(8)
        show_layout.addWidget(self._key_input, 1)
        self._show_btn = QPushButton(tr("Show"))
        self._show_btn.setProperty("variant", "secondary")
        self._show_btn.setCheckable(True)
        self._show_btn.toggled.connect(self._toggle_visibility)
        show_layout.addWidget(self._show_btn)
        self._add_labeled_widget(ai_form, tr("API Key"), key_row)

        self._env_hint = QLabel("")
        self._env_hint.setWordWrap(True)
        self._env_hint.setProperty("muted", True)
        ai_form.addRow("", self._env_hint)

        self._proxy_input = QLineEdit()
        self._proxy_input.setPlaceholderText("http://127.0.0.1:7890")
        self._add_labeled_widget(ai_form, tr("Proxy (optional)"), self._proxy_input)

        proxy_hint = QLabel(tr("Leave empty if no proxy."))
        proxy_hint.setWordWrap(True)
        proxy_hint.setProperty("muted", True)
        ai_form.addRow("", proxy_hint)

        self._language_combo = QComboBox()
        for value, label in LANGUAGE_LABELS.items():
            self._language_combo.addItem(label, value)
        lang_index = self._language_combo.findData(
            self._config.get("ui", {}).get("language", get_language())
        )
        if lang_index >= 0:
            self._language_combo.setCurrentIndex(lang_index)
        self._add_labeled_widget(ui_form, tr("Language"), self._language_combo)

        self._theme_combo = QComboBox()
        for value, label_key in THEME_LABELS.items():
            self._theme_combo.addItem(tr(label_key), value)
        active_theme = normalize_theme(self._config.get("ui", {}).get("theme", "mc"))
        theme_index = self._theme_combo.findData(active_theme)
        if theme_index >= 0:
            self._theme_combo.setCurrentIndex(theme_index)
        self._add_labeled_widget(ui_form, tr("UI Theme"), self._theme_combo)

        self._font_spin = QSpinBox()
        self._font_spin.setRange(8, 32)
        self._font_spin.setValue(int(self._config.get("ui", {}).get("code_font_size", 14)))
        self._add_labeled_widget(ui_form, tr("Code Font Size"), self._font_spin)

        debugger_cfg = self._config.get("debugger", {})
        self._pdb_check = QCheckBox(tr("Enable experimental MSVC/PDB native debugger"))
        self._pdb_check.setChecked(bool(debugger_cfg.get("enable_experimental_pdb", False)))
        advanced_form.addRow("", self._pdb_check)
        pdb_hint = QLabel(
            tr("Requires Windows, Visual Studio Build Tools, and Windows Debugging Tools.")
        )
        pdb_hint.setWordWrap(True)
        pdb_hint.setProperty("muted", True)
        advanced_form.addRow("", pdb_hint)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        save_btn = QPushButton(tr("Save"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _tab_page(self) -> tuple[QScrollArea, QFormLayout]:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(10, 10, 10, 10)
        wrapper_layout.setSpacing(0)

        content = QFrame()
        content.setObjectName("settingsPanel")
        form = QFormLayout(content)
        self._setup_form(form)
        wrapper_layout.addWidget(content, 0)
        wrapper_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(wrapper)
        return scroll, form

    def _setup_form(self, layout: QFormLayout) -> None:
        layout.setContentsMargins(56, 32, 42, 30)
        layout.setHorizontalSpacing(22)
        layout.setVerticalSpacing(18)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

    def _add_labeled_widget(self, layout: QFormLayout, text: str, widget):
        label = QLabel(text)
        label.setProperty("role", "formLabel")
        label.setMinimumWidth(96)
        layout.addRow(label, widget)

    def _fit_to_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(720, 620)
            return
        available = screen.availableGeometry()
        width = min(760, max(620, available.width() - 120))
        height = min(660, max(500, available.height() - 120))
        self.resize(width, height)
        self.setMaximumSize(available.width() - 40, available.height() - 40)

    def _on_provider_changed(self):
        provider = self._provider_combo.currentData()
        if provider:
            self._load_provider_fields(str(provider))

    def _load_provider_fields(self, provider: str):
        cfg = self._provider_config(provider)
        self._model_input.setText(str(cfg.get("model", "")))
        self._base_input.setText(str(cfg.get("api_base", "")))

        env_name = str(cfg.get("api_key_env", ""))
        env_key = os.environ.get(env_name, "") if env_name else ""
        saved_key = str(cfg.get("api_key", ""))
        self._key_input.setText(env_key or saved_key)
        self._env_hint.setText(
            tr("API key can also be set with {env}.", env=env_name or "API_KEY")
        )

        self._proxy_input.setText(str(cfg.get("proxy", "") or self._config.get("llm", {}).get("proxy", "")))

    def _toggle_visibility(self, checked):
        if checked:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText(tr("Hide"))
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText(tr("Show"))

    def _save_and_accept(self):
        provider = str(self._provider_combo.currentData() or "deepseek")
        key = self._key_input.text().strip()
        model = self._model_input.text().strip()
        api_base = self._base_input.text().strip()
        proxy = self._proxy_input.text().strip()
        language = str(self._language_combo.currentData() or "en")
        theme = normalize_theme(self._theme_combo.currentData() or "mc")
        font_size = self._font_spin.value()

        try:
            cfg = self._config or {}
            llm_cfg = cfg.setdefault("llm", {})
            llm_cfg["provider"] = provider
            llm_cfg.setdefault("max_tokens", 8192)
            llm_cfg.setdefault("temperature", 0.0)

            providers = llm_cfg.setdefault("providers", {})
            provider_cfg = dict(DEFAULT_PROVIDERS[provider])
            provider_cfg.update(providers.get(provider, {}) or {})
            if api_base:
                provider_cfg["api_base"] = api_base
            if model:
                provider_cfg["model"] = model
            provider_cfg["api_key"] = key
            if proxy:
                provider_cfg["proxy"] = proxy
                llm_cfg["proxy"] = proxy
            else:
                provider_cfg.pop("proxy", None)
                llm_cfg.pop("proxy", None)
            providers[provider] = provider_cfg

            ui_cfg = cfg.setdefault("ui", {})
            ui_cfg["code_font_size"] = font_size
            ui_cfg["language"] = language
            ui_cfg["theme"] = theme

            debugger_cfg = cfg.setdefault("debugger", {})
            debugger_cfg["enable_experimental_pdb"] = self._pdb_check.isChecked()

            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

            env_name = str(provider_cfg.get("api_key_env", ""))
            if env_name and key:
                os.environ[env_name] = key

            if self.parent():
                try:
                    code_editor = self.parent().code_editor
                    current_font = code_editor.font()
                    current_font.setPointSize(font_size)
                    code_editor.setFont(current_font)
                except Exception:
                    logger.exception("Failed to update editor font")

            load_language(self._config_path)
            self.accept()
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("Error"),
                tr("Failed to save settings: {error}", error=e),
            )


def show_api_key_dialog(parent=None) -> bool:
    config_path = getattr(parent, "_config_path", None)
    dialog = ApiKeyDialog(parent, config_path=config_path)
    return dialog.exec() == QDialog.DialogCode.Accepted


def show_settings_dialog(parent=None) -> bool:
    return show_api_key_dialog(parent)
