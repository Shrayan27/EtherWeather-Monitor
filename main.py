import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from Modbus_Gui import SetUpPage, resource_path

if os.name == 'nt':
    import ctypes
    myappid = 'kbsensormart.weatherstation.gui.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("favicon.png")))
    window = SetUpPage()
    window.show()
    sys.exit(app.exec())