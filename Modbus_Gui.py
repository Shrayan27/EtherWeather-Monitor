import sys
import os


def resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller EXE."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon


class SetUpPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("KB SENSORMART")
        self.setWindowIcon(QIcon(resource_path("favicon.png")))
        self.setStyleSheet(self.get_styles())

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # -------- Card Container ---------
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(15)

        # -------- Title --------
        title = QLabel("Device Setup")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # -------- IP ADDRESS --------
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter Device IP Address")
        card_layout.addWidget(self.ip_input)

        # -------- PORT --------
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Enter Port")
        card_layout.addWidget(self.port_input)

        # -------- MODBUS ADDRESS --------
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Enter Modbus Address")
        card_layout.addWidget(self.address_input)

        # -------- Connect Button --------
        self.connect_button = QPushButton("Connect →")
        self.connect_button.setObjectName("connect_button")
        self.connect_button.clicked.connect(self.connect_device)
        card_layout.addWidget(self.connect_button)

        card.setLayout(card_layout)
        main_layout.addWidget(card)

        self.setLayout(main_layout)

    def connect_device(self):
        host    = self.ip_input.text().strip()
        port    = int(self.port_input.text().strip()) if self.port_input.text().strip() else 4196
        address = int(self.address_input.text().strip()) if self.address_input.text().strip() else 5

        print(f"Connecting to {host}:{port}, Modbus address {address}")

        from Modbus import RawWeatherStation
        from dashboard_page import DashboardPage

        self.station = RawWeatherStation(
            host=host,
            port=port,
            address=address
        )

        self.dashboard = DashboardPage(self.station)
        self.dashboard.show()
        self.close()

    def get_styles(self):
        from datetime import datetime
        hour = datetime.now().hour
        is_day = 5 <= hour < 16

        if is_day:
            return """
            QWidget {
                background-color: #f1f5f9;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #1e293b;
            }

            #card {
                background-color: #ffffff;
                border-radius: 20px;
                border: 2px solid #e2e8f0;
                padding: 40px;
                min-width: 450px;
                max-width: 600px;
            }

            #title {
                background-color: #ffffff;
                color: #0f172a;
                font-size: 32px;
                font-weight: 800;
                margin-bottom: 20px;
            }

            QLineEdit {
                background-color: #f8fafc;
                color: #0f172a;
                padding: 12px 15px;
                border-radius: 10px;
                border: 2px solid #cbd5e1;
                font-size: 16px;
                font-weight: 500;
            }

            QLineEdit:hover {
                border: 2px solid #94a3b8;
            }

            QLineEdit:focus {
                border: 2px solid #3b82f6;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 15px;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                margin-top: 10px;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton:pressed {
                background-color: #1e40af;
            }
            """
        else:
            return """
            QWidget {
                background-color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #f8fafc;
            }

            #card {
                background-color: #1e293b;
                border-radius: 20px;
                border: 2px solid #334155;
                padding: 40px;
                min-width: 450px;
                max-width: 600px;
            }

            #title {
                background-color: #1e293b;
                color: #f8fafc;
                font-size: 32px;
                font-weight: 800;
                margin-bottom: 20px;
            }

            QLineEdit {
                background-color: #334155;
                color: #f8fafc;
                padding: 12px 15px;
                border-radius: 10px;
                border: 2px solid #475569;
                font-size: 16px;
                font-weight: 500;
            }

            QLineEdit:hover {
                border: 2px solid #64748b;
            }

            QLineEdit:focus {
                border: 2px solid #60a5fa;
            }

            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 15px;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                margin-top: 10px;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }

            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SetUpPage()
    window.show()
    sys.exit(app.exec())