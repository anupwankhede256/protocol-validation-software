# app/views/components/graph_panel.py
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget
import pyqtgraph as pg
import random
from PySide6.QtCore import QTimer

class GraphPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UART Signal Graph") 
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(QLabel("Real-Time UART Signal Graph"))
        layout.addWidget(self.plot_widget)
        
        # Buttons for start and stop
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Plot appearance
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Signal Value')
        self.plot_widget.setLabel('bottom', 'Time')

        # Data buffer
        self.x_data = list(range(100))
        self.y_data = [0] * 100
        self.curve = self.plot_widget.plot(self.x_data, self.y_data, pen='b')

        self.timer = QTimer()

        # Initializing the start/stop functionality
        self.start_button.clicked.connect(self.start_data)
        self.stop_button.clicked.connect(self.stop_data)

    def start_data(self):
        """Starts the real-time data updates"""
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(100)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_data(self):
        """Stops the real-time data updates"""
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_graph(self):
        """Updates the graph with new dummy data"""
        new_value = random.randint(0, 100)
        self.y_data = self.y_data[1:] + [new_value]
        self.curve.setData(self.x_data, self.y_data)