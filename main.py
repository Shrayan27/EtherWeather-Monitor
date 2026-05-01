import sys
from PyQt6.QtWidgets import QApplication
from Modbus_Gui import SetUpPage

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SetUpPage()
    window.show()
    sys.exit(app.exec())