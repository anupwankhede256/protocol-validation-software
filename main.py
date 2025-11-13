# main.py
import sys
from PySide6.QtWidgets import QApplication
from landing_page import FirstPage

def main():
    app = QApplication(sys.argv)
    window = FirstPage()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()