from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QComboBox, QLineEdit, QFileDialog, QMessageBox, QFrame,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

from app_parameters import (
    APP_TITLE, SENSOR_ROWS, SENSOR_COLS,
    DEFAULT_MIN_TEMP_C, DEFAULT_MAX_TEMP_C,
    CSV_FILENAME_PREFIX
)

class AppGUI(QMainWindow):
    connect_signal = pyqtSignal(str)
    disconnect_signal = pyqtSignal()
    start_record_signal = pyqtSignal(str, int)
    stop_record_signal = pyqtSignal()
    select_file_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, 900, 750)

        self.current_heatmap_data = np.zeros((SENSOR_ROWS, SENSOR_COLS), dtype=np.float32)
        self.current_min_temp = DEFAULT_MIN_TEMP_C
        self.current_max_temp = DEFAULT_MAX_TEMP_C
        self.current_center_temp = (DEFAULT_MIN_TEMP_C + DEFAULT_MAX_TEMP_C) / 2

        self.recording_duration_str = "60"

        self.create_widgets()
        self.setup_heatmap()

    def create_widgets(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        serial_frame_container, serial_frame_layout_for_content = self._create_section_frame_with_layout("Conexión Serial")
        serial_layout = QHBoxLayout()
        serial_frame_layout_for_content.addLayout(serial_layout)
        serial_layout.addWidget(QLabel("Puerto COM:"))
        self.port_combobox = QComboBox()
        self.port_combobox.setPlaceholderText("Selecciona un puerto")
        serial_layout.addWidget(self.port_combobox)
        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self._on_connect_button_click)
        serial_layout.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("Desconectar")
        self.disconnect_button.clicked.connect(self.disconnect_signal.emit)
        self.disconnect_button.setEnabled(False)
        serial_layout.addWidget(self.disconnect_button)
        main_layout.addWidget(serial_frame_container)

        heatmap_frame_container, heatmap_frame_layout_for_content = self._create_section_frame_with_layout("Mapa de Calor")
        self.heatmap_layout = QVBoxLayout()
        heatmap_frame_layout_for_content.addLayout(self.heatmap_layout)
        main_layout.addWidget(heatmap_frame_container, 1)

        stats_frame_container, stats_frame_layout_for_content = self._create_section_frame_with_layout("Estadísticas de Temperatura")
        stats_layout = QHBoxLayout()
        stats_frame_layout_for_content.addLayout(stats_layout)
        self.min_temp_label = QLabel(f"Mínima: {self.current_min_temp:.1f}°C")
        self.max_temp_label = QLabel(f"Máxima: {self.current_max_temp:.1f}°C")
        self.center_temp_label = QLabel(f"Centro: {self.current_center_temp:.1f}°C")
        font = QFont()
        font.setPointSize(12)
        self.min_temp_label.setFont(font)
        self.max_temp_label.setFont(font)
        self.center_temp_label.setFont(font)
        stats_layout.addWidget(self.min_temp_label, 1, Qt.AlignLeft)
        stats_layout.addWidget(self.max_temp_label, 1, Qt.AlignCenter)
        stats_layout.addWidget(self.center_temp_label, 1, Qt.AlignRight)
        main_layout.addWidget(stats_frame_container)

        record_frame_container, record_frame_layout_for_content = self._create_section_frame_with_layout("Registro de Datos")
        record_layout = QVBoxLayout()
        record_frame_layout_for_content.addLayout(record_layout)
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duración (segundos):"))
        self.duration_entry = QLineEdit(self.recording_duration_str)
        self.duration_entry.setFixedWidth(80)
        duration_layout.addWidget(self.duration_entry)
        duration_layout.addStretch(1)
        record_layout.addLayout(duration_layout)
        file_selection_layout = QHBoxLayout()
        self.select_file_button = QPushButton("Seleccionar Archivo CSV")
        self.select_file_button.clicked.connect(self.select_file_signal.emit)
        file_selection_layout.addWidget(self.select_file_button)
        self.save_path_label = QLabel("Ruta: No seleccionado")
        self.save_path_label.setWordWrap(True)
        file_selection_layout.addWidget(self.save_path_label, 1)
        record_layout.addLayout(file_selection_layout)
        record_buttons_layout = QHBoxLayout()
        self.start_record_button = QPushButton("Iniciar Registro")
        self.start_record_button.clicked.connect(self._on_start_record_click)
        self.start_record_button.setEnabled(False)
        record_buttons_layout.addWidget(self.start_record_button)
        self.stop_record_button = QPushButton("Detener Registro")
        self.stop_record_button.clicked.connect(self.stop_record_signal.emit)
        self.stop_record_button.setEnabled(False)
        record_buttons_layout.addWidget(self.stop_record_button)
        record_layout.addLayout(record_buttons_layout)
        main_layout.addWidget(record_frame_container)

    def _create_section_frame_with_layout(self, title):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLineWidth(1)
        main_frame_layout = QVBoxLayout(frame)
        main_frame_layout.setContentsMargins(5, 5, 5, 5)
        main_frame_layout.setSpacing(5)
        label = QLabel(f"<b>{title}</b>")
        label.setFont(QFont("Arial", 10))
        main_frame_layout.addWidget(label)
        main_frame_layout.setAlignment(label, Qt.AlignLeft | Qt.AlignTop)
        content_layout = QVBoxLayout()
        main_frame_layout.addLayout(content_layout)
        return frame, content_layout

    def setup_heatmap(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.canvas = FigureCanvas(self.fig)
        self.heatmap_layout.addWidget(self.canvas)
        self.heatmap_im = self.ax.imshow(
            self.current_heatmap_data,
            cmap='jet',
            vmin=DEFAULT_MIN_TEMP_C,
            vmax=DEFAULT_MAX_TEMP_C,
            interpolation='none'
        )
        self.ax.set_title("Mapa de Calor del Sensor")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.colorbar = self.fig.colorbar(self.heatmap_im, ax=self.ax, orientation='vertical', fraction=0.046, pad=0.04)
        self.colorbar.set_label("Temperatura (°C)")
        self.fig.tight_layout()

    def update_port_list(self, ports):
        self.port_combobox.clear()
        if ports:
            self.port_combobox.addItems(ports)
            self.port_combobox.setCurrentIndex(0)
            self.connect_button.setEnabled(True)
        else:
            self.port_combobox.setPlaceholderText("No se encontraron puertos")
            self.connect_button.setEnabled(False)

    def update_heatmap(self, data):
        """
        Actualiza los datos del mapa de calor y la barra de color.
        data: numpy array (SENSOR_ROWS, SENSOR_COLS)
        """
        if data is None:
            return

        # Redimensionar el imshow si los datos tienen una forma diferente
        # (Esto es crucial para soportar AMG8833 y MLX90640 dinámicamente)
        if self.heatmap_im.get_array().shape != data.shape:
            self.ax.clear() # Limpiar el eje actual
            self.heatmap_im = self.ax.imshow(
                data,
                cmap='jet',
                vmin=DEFAULT_MIN_TEMP_C,
                vmax=DEFAULT_MAX_TEMP_C,
                interpolation='none'
            )
            self.ax.set_title("Mapa de Calor del Sensor")
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            # Quitar la colorbar vieja si existe y añadir la nueva
            if hasattr(self, 'colorbar') and self.colorbar:
                self.colorbar.remove()
            self.colorbar = self.fig.colorbar(self.heatmap_im, ax=self.ax, orientation='vertical', fraction=0.046, pad=0.04)
            self.colorbar.set_label("Temperatura (°C)")
            self.fig.tight_layout()
        else:
            self.heatmap_im.set_array(data)

        p_min = np.percentile(data, 1)
        p_max = np.percentile(data, 99)

        if p_max - p_min < 0.1:
            p_min -= 0.5
            p_max += 0.5

        # This line correctly sets the color limits for the image.
        # The colorbar automatically reflects these limits.
        self.heatmap_im.set_clim(vmin=p_min, vmax=p_max)

        # self.colorbar.draw_all() # <--- THIS LINE IS THE ONE TO REMOVE

        self.canvas.draw() # This redraws the entire canvas, updating the heatmap and colorbar

    def update_stats(self, min_val, max_val, center_val):
        self.min_temp_label.setText(f"Mínima: {min_val:.1f}°C")
        self.max_temp_label.setText(f"Máxima: {max_val:.1f}°C")
        self.center_temp_label.setText(f"Centro: {center_val:.1f}°C")

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def _on_connect_button_click(self):
        selected_port = self.port_combobox.currentText()
        if not selected_port or selected_port == "No se encontraron puertos":
            self.show_error("Error de Conexión", "Por favor, selecciona un puerto COM válido.")
            return
        self.connect_signal.emit(selected_port)

    def _on_start_record_click(self):
        try:
            duration = int(self.duration_entry.text())
            if duration <= 0:
                raise ValueError("La duración debe ser un número positivo.")
            save_path = self.save_path_label.text().replace("Ruta: ", "")
            if save_path == "No seleccionado" or not save_path:
                self.show_error("Error de Registro", "Por favor, selecciona una ruta para guardar el archivo CSV.")
                return
            self.start_record_signal.emit(save_path, duration)
        except ValueError as e:
            self.show_error("Error de Entrada", f"Duración inválida: {e}")

    def set_connection_buttons_state(self, connected):
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.port_combobox.setEnabled(not connected)
        if connected:
            if self.save_path_label.text() != "Ruta: No seleccionado":
                self.start_record_button.setEnabled(True)
        else:
            self.start_record_button.setEnabled(False)
            self.stop_record_button.setEnabled(False)

    def set_record_buttons_state(self, recording):
        self.start_record_button.setEnabled(not recording and self.disconnect_button.isEnabled())
        self.stop_record_button.setEnabled(recording)
        self.duration_entry.setEnabled(not recording)
        self.select_file_button.setEnabled(not recording)

    def set_save_path_display(self, path):
        self.save_path_label.setText(f"Ruta: {path}")
        if self.disconnect_button.isEnabled():
             self.start_record_button.setEnabled(True)
        else:
             self.start_record_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication([])
    gui = AppGUI()
    gui.update_port_list(["COM1", "COM3", "/dev/ttyUSB0"])
    test_data = np.random.rand(SENSOR_ROWS, SENSOR_COLS) * 10 + 25
    gui.update_heatmap(test_data)
    gui.update_stats(np.min(test_data), np.max(test_data), test_data[SENSOR_ROWS//2, SENSOR_COLS//2])
    gui.set_connection_buttons_state(True)
    gui.set_save_path_display("/home/user/test_log.csv")
    gui.connect_signal.connect(lambda p: print(f"Conectar a: {p}"))
    gui.disconnect_signal.connect(lambda: print("Desconectar"))
    gui.start_record_signal.connect(lambda p, d: print(f"Iniciar registro en {p} por {d}s"))
    gui.stop_record_signal.connect(lambda: print("Detener registro"))
    gui.select_file_signal.connect(lambda: print("Seleccionar archivo (acción simulada)"))
    gui.show()
    app.exec_()
