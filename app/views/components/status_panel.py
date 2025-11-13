# app/views/components/status_panel.py
from PySide6.QtWidgets import QGroupBox, QTextEdit, QPushButton, QVBoxLayout
from datetime import datetime

class StatusPanel(QGroupBox):
    def __init__(self):
        super().__init__("LIVE ACTIVITY LOG")
        self.setMinimumWidth(300)
        self.setLayout(QVBoxLayout())

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout().addWidget(self.log_output)

        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setStyleSheet("font-weight: bold;")
        self.clear_btn.clicked.connect(self.clear_logs)
        self.layout().addWidget(self.clear_btn)

    def append_message(self, message: str, level: str = "info"):
        """Append a message with timestamp and color based on level."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = {
            "info": "black",
            "warning": "orange",
            "error": "red",
            "debug": "gray"
        }.get(level.lower(), "black")

        safe_message = (
            message.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
        )

        formatted_message = (
        f'<div style="margin-bottom:4px;">'
        f'<span style="color:gray;">[{timestamp}]</span><br>'
        f'<span style="color:{color};">{safe_message}</span>'
        f'</div>'
    )
        self.log_output.append(formatted_message)

    def clear_logs(self):
        self.log_output.clear()