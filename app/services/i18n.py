from pathlib import Path

import yaml


LANG_EN = "en"
LANG_ZH = "zh"

LANGUAGE_LABELS = {
    LANG_EN: "English",
    LANG_ZH: "中文",
}

_language = LANG_EN


TRANSLATIONS = {
    LANG_ZH: {
        "C++ Memory Visualizer": "C++ 内存可视化器",
        "Home": "首页",
        "Code Editor": "代码编辑器",
        "OJ Analysis": "OJ 分析",
        "File Import": "文件导入",
        "Review": "错题复习",
        "Knowledge Base": "知识库",
        "Example:": "示例：",
        "Run": "运行",
        "Next Step": "下一步",
        "Prev Step": "上一步",
        "Reset": "重置",
        "Settings": "设置",
        "AI Settings...": "AI 设置...",
        "API Key...": "API 设置...",
        "Auto Fit": "自动适配",
        "Ready": "就绪",
        "Analyzing code with AI...": "正在用 AI 分析代码...",
        "// Enter C++ code here...": "// 在这里输入 C++ 代码...",
        "Zoom Out (Ctrl+-)": "缩小 (Ctrl+-)",
        "Zoom In (Ctrl+=)": "放大 (Ctrl+=)",
        "Fit to View": "适配视图",
        "Ready - Enter C++ code and click Run": "就绪 - 输入 C++ 代码并点击运行",
        "Code loaded - click Run to visualize": "代码已载入 - 点击运行开始可视化",
        "Step {current}/{total}": "步骤 {current}/{total}",
        "AI Settings": "AI 设置",
        "Provider": "供应商",
        "Model": "模型",
        "API Base": "API 地址",
        "API Key": "API Key",
        "Proxy (optional)": "代理（可选）",
        "Language": "语言",
        "Code Font Size": "代码字号",
        "Show": "显示",
        "Hide": "隐藏",
        "Cancel": "取消",
        "Save": "保存",
        "Skip (Offline)": "跳过（离线）",
        "API key can also be set with {env}.": "也可以通过环境变量 {env} 设置 API key。",
        "Leave empty if no proxy.": "没有代理可留空。",
        "Settings saved. Restart the app to update every page.": "设置已保存。重启应用后所有页面都会更新。",
        "Failed to save settings: {error}": "保存设置失败：{error}",
        "Error": "错误",
        "API key not configured - click Settings or set provider API key": "API key 未配置 - 请点击设置或配置当前供应商的 API key",
        "No code to run": "没有可运行的代码",
        "Sending code to AI...": "正在发送代码给 AI...",
        "AI returned empty trace": "AI 返回了空执行轨迹",
        "Execution Error": "执行错误",
    }
}


def set_language(language: str | None):
    global _language
    _language = language if language in LANGUAGE_LABELS else LANG_EN


def get_language() -> str:
    return _language


def load_language(config_path: Path | None = None):
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    language = LANG_EN
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            language = cfg.get("ui", {}).get("language", LANG_EN)
        except Exception:
            language = LANG_EN

    set_language(language)


def tr(text: str, **kwargs) -> str:
    translated = TRANSLATIONS.get(_language, {}).get(text, text)
    if kwargs:
        try:
            return translated.format(**kwargs)
        except Exception:
            return translated
    return translated
