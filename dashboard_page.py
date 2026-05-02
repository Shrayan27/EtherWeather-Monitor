from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QGridLayout, QHBoxLayout,
    QFrame, QLineEdit, QDialog, QMessageBox, QFileDialog
)

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
import json
import os
import sys
import time

def resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller EXE."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# -------- Background Sensor Worker --------
class SensorWorker(QThread):
    """Runs Modbus reads in a background thread so the UI stays responsive."""
    data_ready = pyqtSignal(dict)

    def __init__(self, station, command):
        super().__init__()
        self.station = station
        self.command = command
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                response = self.station.send_command(self.command)
                if response:
                    data = self.station.parse_data(response)
                    if data:
                        self.data_ready.emit(data)
            except Exception as e:
                print(f"[SensorWorker] Error: {e}")
            self.msleep(1000)

    def stop(self):
        self._running = False
        self.wait(3000)


class ConfigDialog(QDialog):
    def __init__(self, station, parent=None):
        super().__init__(parent)
        self.station = station

        self.setWindowTitle("Device Configuration")
        self.setFixedWidth(450)
        self.setStyleSheet(self.get_dialog_styles())

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QLabel("SENSOR SETUP")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Update communication parameters for the connected station.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # --- Device Address Card ---
        addr_card = QFrame()
        addr_card.setObjectName("card")
        addr_layout = QVBoxLayout(addr_card)

        addr_label = QLabel("🏠 DEVICE ADDRESS")
        addr_label.setObjectName("section_title")
        addr_layout.addWidget(addr_label)

        self.addr_input = QLineEdit()
        self.addr_input.setPlaceholderText(f"Current: {getattr(self.station, 'address', 5)}")
        addr_layout.addWidget(self.addr_input)

        layout.addWidget(addr_card)

        # --- Warning ---
        warning = QLabel("⚠ Changing address will reboot the sensor (approx. 2s delay).")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addStretch()

        # Apply Button
        self.apply_btn = QPushButton("APPLY CHANGES")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.clicked.connect(self.apply_config)
        layout.addWidget(self.apply_btn)

        self.setLayout(layout)

    def get_dialog_styles(self):
        from datetime import datetime
        hour = datetime.now().hour
        is_day = 5 <= hour < 16

        if is_day:
            return """
            QDialog { background-color: #f1f5f9; }

            #header {
                color: #0f172a; font-size: 22px; font-weight: 800;
                letter-spacing: 2px; margin-bottom: 5px;
            }
            #subtitle { color: #64748b; font-size: 13px; margin-bottom: 15px; }
            #card {
                background-color: #ffffff; border: 2px solid #e2e8f0;
                border-radius: 12px; padding: 15px;
            }
            #section_title {
                color: #2563eb; font-size: 11px; font-weight: 700;
                letter-spacing: 1px; margin-bottom: 8px;
            }
            QLineEdit {
                background-color: #f8fafc; border: 1px solid #e2e8f0;
                border-radius: 8px; padding: 10px; color: #1e293b; font-size: 14px;
            }
            QLineEdit:hover { border: 1px solid #2563eb; }
            #warning { color: #ea580c; font-size: 11px; font-style: italic; margin-top: 5px; }
            #apply_btn {
                background-color: #2563eb; color: white; padding: 15px;
                border-radius: 10px; font-size: 14px; font-weight: 900; letter-spacing: 1px;
            }
            #apply_btn:hover { background-color: #1d4ed8; }
            """
        else:
            return """
            QDialog { background-color: #0f172a; }

            #header {
                color: #f8fafc; font-size: 22px; font-weight: 800;
                letter-spacing: 2px; margin-bottom: 5px;
            }
            #subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 15px; }
            #card {
                background-color: #1e293b; border: 1px solid #334155;
                border-radius: 12px; padding: 15px;
            }
            #section_title {
                color: #60a5fa; font-size: 11px; font-weight: 700;
                letter-spacing: 1px; margin-bottom: 8px;
            }
            QLineEdit {
                background-color: #0f172a; border: 1px solid #334155;
                border-radius: 8px; padding: 10px; color: #f8fafc; font-size: 14px;
            }
            QLineEdit:hover { border: 1px solid #3b82f6; }
            #warning { color: #fbbf24; font-size: 11px; font-style: italic; margin-top: 5px; }
            #apply_btn {
                background-color: #3b82f6; color: white; padding: 15px;
                border-radius: 10px; font-size: 14px; font-weight: 900; letter-spacing: 1px;
            }
            #apply_btn:hover { background-color: #2563eb; }
            """

    def apply_config(self):
        try:
            addr_text = self.addr_input.text().strip()
            if not addr_text:
                return
            new_addr = int(addr_text)
            if not (1 <= new_addr <= 247):
                raise ValueError("Address must be 1-247")
            parent = self.parent()

            # stop polling first
            if parent and parent.worker:
                parent.stop_reading()

            ok = self.station.change_address_full_sequence(
                new_addr
            )

            if not ok:
                raise Exception(
                    "Sensor did not accept new address"
                )

            # update dashboard command
            if parent:
                parent.command = [
                    new_addr,
                    0x03,
                    0x00,
                    0x00,
                    0x00,
                    0x60
                ]

            time.sleep(1.5)

            # restart reading using NEW address
            if parent:
                parent.start_reading()

            QMessageBox.information(
                self,
                "Success",
                f"Device address changed to {new_addr}"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Config Error",
                str(e)
            )


class DashboardPage(QWidget):
    def __init__(self, station):
        super().__init__()

        self.station = station
        self.worker = None

        self.setGeometry(100, 100, 800, 650)
        self.setWindowTitle("KB SENSORMART")
        self.setWindowIcon(QIcon(resource_path("favicon.png")))
        self.setStyleSheet(self.get_styles())

        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Smart Weather Station")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # -------- Configuration Panel ---------
        config_card = QFrame()
        config_card.setObjectName("card")
        config_layout = QHBoxLayout()

        host    = getattr(self.station, 'host', 'Unknown')
        port    = getattr(self.station, 'port', 'Unknown')

        info_label = QLabel(f"IP: {host}   |   Port: {port}")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        config_layout.addWidget(info_label)

        config_layout.addStretch()

        self.configure_btn = QPushButton("Change Device Address")
        self.configure_btn.clicked.connect(self.open_config_dialog)
        config_layout.addWidget(self.configure_btn)

        config_layout.addSpacing(30)
        self.log_path_label = QLabel("weather.csv")
        self.log_path_label.setStyleSheet("font-size: 12px; color: #64748b; font-style: italic;")
        config_layout.addWidget(self.log_path_label)

        self.choose_file_btn = QPushButton("Choose File")
        self.choose_file_btn.setFixedWidth(130)
        self.choose_file_btn.clicked.connect(self.choose_log_file)
        config_layout.addWidget(self.choose_file_btn)

        config_card.setLayout(config_layout)
        main_layout.addWidget(config_card)

        # -------- Timestamp --------
        self.timestamp_label = QLabel("Last Updated: --")
        self.timestamp_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #64748b;")
        self.timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.timestamp_label)

        # -------- Data Grid Card --------
        data_card = QFrame()
        data_card.setObjectName("card")
        grid = QGridLayout()
        grid.setSpacing(25)
        self.labels = {}

        # Rainfall removed, Pressure renamed to Barometric Pressure
        sensors = [
            "Temperature", "Humidity",
            "Barometric Pressure", "Wind Speed",
            "Wind Direction"
        ]

        for i, sensor in enumerate(sensors):
            label = QLabel(sensor.upper())
            value = QLabel("--")
            value.setObjectName("value")

            row = i // 2
            col = (i % 2) * 2

            grid.addWidget(label, row, col)
            grid.addWidget(value, row, col + 1)

            self.labels[sensor] = value

        data_card.setLayout(grid)
        main_layout.addWidget(data_card)

        # -------- Buttons --------
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_reading)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_reading)
        button_layout.addWidget(self.stop_button)

        self.store_button = QPushButton("Store")
        self.store_button.clicked.connect(self.store_data)
        button_layout.addWidget(self.store_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setObjectName("disconnect_btn")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        button_layout.addWidget(self.disconnect_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # Modbus command: Read 96 registers from address 0
        self.command = [getattr(self.station, 'address', 5), 0x03, 0x00, 0x00, 0x00, 0x60]
        self.latest_data = None

        self.is_logging = False

        from Modbus import CSVLogger
        self.logger = CSVLogger()

        # Load persistent settings
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))

        self.settings_file = os.path.join(app_dir, "settings.json")
        self.log_filepath  = os.path.join(app_dir, "weather.csv")
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                print(f"Settings loaded.")
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            settings = {}
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def start_reading(self):

        if self.worker:
            self.worker.stop()

        self.worker = SensorWorker(
            self.station,
            self.command
        )

        self.worker.data_ready.connect(
            self.on_data_ready
        )

        self.worker.start()

    def stop_reading(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

    def on_data_ready(self, data):
        """Called from the worker thread via signal — safe to update UI here."""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.setText(f"Last Updated: {current_time}")

        self.latest_data = data

        # Update UI labels
        self.labels["Temperature"].setText(f"{data['temperature']:.2f} °C")
        self.labels["Humidity"].setText(f"{data['humidity']:.2f} %")
        self.labels["Barometric Pressure"].setText(f"{data['pressure']:.2f} hPa")
        self.labels["Wind Speed"].setText(f"{data['wind_speed']:.2f} m/s")
        self.labels["Wind Direction"].setText(f"{int(data['wind_direction'])} °")

        # Auto-log if enabled
        if self.is_logging:
            try:
                self.logger.log(data)
            except Exception as e:
                print(f"[Dashboard] Logging error: {e}")

    # ------ Choose Log File ------
    def choose_log_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Choose CSV Log File",
            self.log_filepath,
            "CSV Files (*.csv);;All Files (*)",
            options=QFileDialog.Option.DontConfirmOverwrite
        )
        if not filepath:
            return
        if not filepath.lower().endswith(".csv"):
            filepath += ".csv"
        self.log_filepath = filepath
        short_name = os.path.basename(filepath)
        self.log_path_label.setText(f"{short_name}")
        self.log_path_label.setStyleSheet("font-size: 12px; color: #64748b; font-style: italic;")
        print(f"Log file set to: {filepath}")

    # ------ Store ------
    def store_data(self):
        if not self.is_logging:
            from Modbus import CSVLogger
            self.logger = CSVLogger(self.log_filepath)
            self.is_logging = True

            short_name = os.path.basename(self.log_filepath)
            self.log_path_label.setText(f"Logging → {short_name}")
            self.log_path_label.setStyleSheet("font-size: 12px; color: #10b981; font-weight: bold;")
            self.choose_file_btn.setEnabled(False)

            self.store_button.setText("Stop Logging")
            self.store_button.setStyleSheet("background-color: #10b981; color: white;")
            print(f"Real-time Logging Started → {self.log_filepath}")

        else:
            self.is_logging = False
            short_name = os.path.basename(self.log_filepath)
            self.log_path_label.setText(f"{short_name}")
            self.log_path_label.setStyleSheet("font-size: 12px; color: #64748b; font-style: italic;")
            self.choose_file_btn.setEnabled(True)

            self.store_button.setText("Store")
            self.store_button.setStyleSheet("")
            print("Real-time Logging Stopped!")

    def open_config_dialog(self):
        dialog = ConfigDialog(self.station, self)
        dialog.exec()

    # ------ Disconnect -------
    def disconnect_device(self):
        self.stop_reading()
        if self.station and hasattr(self.station, 'sock') and self.station.sock:
            self.station.close()
            print("Device Disconnected!")

        from Modbus_Gui import SetUpPage
        self.setup_window = SetUpPage()
        self.setup_window.show()
        self.close()

    # -------- Styles --------
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
            #title {
                background-color: transparent;
                font-size: 32px; font-weight: 800;
                margin-bottom: 10px; color: #0f172a;
            }
            #card {
                background-color: #ffffff;
                border-radius: 20px; border: 2px solid #e2e8f0; padding: 30px;
            }
            QLabel {
                background-color: transparent;
                font-size: 15px; font-weight: 700;
                color: #64748b; letter-spacing: 1px;
            }
            #value {
                background-color: transparent;
                color: #2563eb; font-size: 28px; font-weight: 800;
            }
            QPushButton {
                background-color: #2563eb; color: white;
                padding: 15px; border-radius: 12px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            #disconnect_btn { background-color: #ef4444; }
            #disconnect_btn:hover { background-color: #dc2626; }
            #disconnect_btn:pressed { background-color: #b91c1c; }
            QLineEdit {
                background-color: #f8fafc; border: 2px solid #e2e8f0;
                border-radius: 8px; padding: 10px;
                color: #1e293b; font-size: 14px; font-weight: bold;
            }
            QLineEdit:focus { border: 2px solid #2563eb; }
            QLineEdit:disabled { background-color: #e2e8f0; color: #94a3b8; }
            """
        else:
            return """
            QWidget {
                background-color: #0f172a;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #f8fafc;
            }
            #title {
                background-color: transparent;
                font-size: 32px; font-weight: 800;
                margin-bottom: 10px; color: #f8fafc;
            }
            #card {
                background-color: #1e293b;
                border-radius: 20px; border: 2px solid #334155; padding: 30px;
            }
            QLabel {
                background-color: transparent;
                font-size: 15px; font-weight: 700;
                color: #94a3b8; letter-spacing: 1px;
            }
            #value {
                background-color: transparent;
                color: #60a5fa; font-size: 28px; font-weight: 800;
            }
            QPushButton {
                background-color: #3b82f6; color: white;
                padding: 15px; border-radius: 12px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
            #disconnect_btn { background-color: #ef4444; }
            #disconnect_btn:hover { background-color: #dc2626; }
            #disconnect_btn:pressed { background-color: #b91c1c; }
            QLineEdit {
                background-color: #0f172a; border: 2px solid #334155;
                border-radius: 8px; padding: 10px;
                color: #f8fafc; font-size: 14px; font-weight: bold;
            }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            QLineEdit:disabled { background-color: #1e293b; color: #475569; }
            """