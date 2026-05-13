from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class MainMenuPage(QWidget):
    start_requested = Signal()
    sandbox_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        title = QLabel("C++ 内存实验室")
        title.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        title.setStyleSheet("color: #E8A840;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("指针与动态内存可视化教学")
        subtitle.setFont(QFont("Microsoft YaHei", 13))
        subtitle.setStyleSheet("color: #AAA;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        btn_style = """
            QPushButton {
                background-color: #3a3a5e;
                color: white;
                border: 2px solid #4A90D9;
                border-radius: 6px;
                padding: 10px 40px;
                font-size: 15px;
                font-family: "Microsoft YaHei";
                min-width: 260px;
            }
            QPushButton:hover {
                background-color: #4A90D9;
            }
        """

        start_btn = QPushButton("开始学习")
        start_btn.setStyleSheet(btn_style)
        start_btn.clicked.connect(self.start_requested.emit)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)

        layout.addSpacing(10)

        exit_btn = QPushButton("退出")
        exit_btn.setStyleSheet(btn_style.replace("#4A90D9", "#555"))
        exit_btn.clicked.connect(self.exit_requested.emit)
        layout.addWidget(exit_btn, alignment=Qt.AlignCenter)

        self.setStyleSheet("background-color: #14142a;")
