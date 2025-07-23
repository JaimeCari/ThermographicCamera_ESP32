import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QStatusBar, QFileDialog,
                             QGroupBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from collections import deque
import time
import csv
from datetime import datetime
import os

from app_parameters import (
    MAX_PLOT_POINTS, APP_WINDOW_TITLE, TEMP_DISPLAY_STYLE,
    CSV_HEADERS, CSV_FILE_FILTER,
    COMMAND_SERVO_OPEN, COMMAND_SERVO_CLOSE,
    DEFAULT_CYCLE_COUNT, DEFAULT_INTERVAL_SEC,
    DATA_REQUEST_INTERVAL_MS
)
from serial_handler import SerialReader, list_available_ports

class ArduinoControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.current_servo_state = "Cerrado"
        self.is_connected = False

        self.time_data = deque(maxlen=MAX_PLOT_POINTS)
        self.temp_data = deque(maxlen=MAX_PLOT_POINTS)
        self.start_time = None

        self.csv_file = None
        self.csv_writer = None
        self.is_logging = False
        self.logging_started_by_cycle = False
        self.manual_logging_timer = QTimer(self)
        self.manual_logging_timer.timeout.connect(self.auto_stop_logging)

        self.data_request_timer = QTimer(self)
        self.data_request_timer.timeout.connect(self.request_temperature_from_arduino)
        self.data_request_timer.setInterval(DATA_REQUEST_INTERVAL_MS)

        self.cycle_timer = QTimer(self)
        self.cycle_timer.timeout.connect(self.run_cycle_step)
        self.current_cycle = 0
        self.total_cycles = 0
        self.interval_duration = 0.0
        self.cycle_step = 0

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.setGeometry(100, 100, 1000, 700)

        main_layout = QVBoxLayout()

        self.statusBar = QStatusBar()
        main_layout.addWidget(self.statusBar)
        self.statusBar.showMessage("Listo para conectar.")

        top_layout = QHBoxLayout()

        connection_group = QGroupBox("Conexión Serial")
        connection_layout = QVBoxLayout()

        port_refresh_layout = QHBoxLayout()
        port_refresh_layout.addWidget(QLabel("Puerto COM:"))
        self.port_selector = QComboBox()
        self.populate_ports()
        port_refresh_layout.addWidget(self.port_selector)

        self.refresh_button = QPushButton("Refrescar Puertos")
        self.refresh_button.clicked.connect(self.populate_ports)
        port_refresh_layout.addWidget(self.refresh_button)
        connection_layout.addLayout(port_refresh_layout)

        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        connection_group.setLayout(connection_layout)
        top_layout.addWidget(connection_group)

        temp_time_group = QGroupBox("Datos en Vivo")
        temp_time_layout = QVBoxLayout()

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperatura Actual:"))
        self.temperature_display = QLabel("---.-- °C")
        self.temperature_display.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
        temp_layout.addWidget(self.temperature_display, alignment=Qt.AlignCenter)
        temp_time_layout.addLayout(temp_layout)

        elapsed_layout = QHBoxLayout()
        elapsed_layout.addWidget(QLabel("Tiempo Transcurrido:"))
        self.elapsed_time_display = QLabel("0.00 s")
        self.elapsed_time_display.setStyleSheet("font-size: 18px; color: green;")
        elapsed_layout.addWidget(self.elapsed_time_display, alignment=Qt.AlignCenter)
        temp_time_layout.addLayout(elapsed_layout)

        temp_time_group.setLayout(temp_time_layout)
        top_layout.addWidget(temp_time_group)

        main_layout.addLayout(top_layout)

        center_layout = QHBoxLayout()

        plot_group = QGroupBox("Gráfica de Temperatura")
        plot_layout = QVBoxLayout()
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)

        self.ax.set_title("Temperatura vs. Tiempo")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel("Temperatura (°C)")
        self.ax.grid(True)

        self.line, = self.ax.plot([], [], 'r-')
        self.figure.tight_layout()
        plot_group.setLayout(plot_layout)
        center_layout.addWidget(plot_group, 3)

        control_column_layout = QVBoxLayout()

        manual_servo_group = QGroupBox("Control Manual y Registro")
        manual_servo_layout = QVBoxLayout()

        self.open_servo_button = QPushButton("Abrir Servo (O)")
        self.open_servo_button.clicked.connect(self.send_open_command)
        manual_servo_layout.addWidget(self.open_servo_button)

        self.close_servo_button = QPushButton("Cerrar Servo (C)")
        self.close_servo_button.clicked.connect(self.send_close_command)
        manual_servo_layout.addWidget(self.close_servo_button)

        manual_servo_layout.addStretch(0)
        manual_servo_layout.addWidget(QLabel("--- Registro Manual ---"))

        logging_duration_control_layout = QHBoxLayout()
        logging_duration_control_layout.addWidget(QLabel("Duración (segundos):"))

        self.logging_duration_spinbox = QDoubleSpinBox()
        self.logging_duration_spinbox.setMinimum(0.0)
        self.logging_duration_spinbox.setMaximum(3600.0)
        self.logging_duration_spinbox.setSingleStep(0.1)
        self.logging_duration_spinbox.setValue(0.0)

        logging_duration_control_layout.addWidget(self.logging_duration_spinbox)

        self.help_duration_button = QPushButton("?")
        self.help_duration_button.setFixedSize(24, 24)
        self.help_duration_button.clicked.connect(self.toggle_duration_help_text)
        self.help_duration_button.setToolTip("Click para ver/ocultar información sobre la duración del registro.")
        logging_duration_control_layout.addWidget(self.help_duration_button)
        manual_servo_layout.addLayout(logging_duration_control_layout)

        self.duration_help_label = QLabel("Ingrese **0.0** para un registro de tiempo **indefinido**. Cualquier valor positivo detendrá el registro automáticamente después de ese tiempo.")
        self.duration_help_label.setWordWrap(True)
        self.duration_help_label.setStyleSheet("color: gray; font-size: 10px; margin-left: 5px;")
        self.duration_help_label.hide()
        manual_servo_layout.addWidget(self.duration_help_label)

        self.start_logging_button = QPushButton("Iniciar Registro")
        self.start_logging_button.clicked.connect(self.start_logging)
        manual_servo_layout.addWidget(self.start_logging_button)

        self.stop_logging_button = QPushButton("Detener Registro")
        self.stop_logging_button.clicked.connect(self.stop_logging)
        manual_servo_layout.addWidget(self.stop_logging_button)

        manual_servo_group.setLayout(manual_servo_layout)
        control_column_layout.addWidget(manual_servo_group)

        cycle_mode_group = QGroupBox("Modo de Ciclos (Servo)")
        cycle_mode_layout = QVBoxLayout()

        cycle_count_layout = QHBoxLayout()
        cycle_count_layout.addWidget(QLabel("Número de Ciclos:"))
        self.cycle_spinbox = QSpinBox()
        self.cycle_spinbox.setMinimum(1)
        self.cycle_spinbox.setMaximum(1000)
        self.cycle_spinbox.setValue(DEFAULT_CYCLE_COUNT)
        cycle_count_layout.addWidget(self.cycle_spinbox)
        cycle_mode_layout.addLayout(cycle_count_layout)

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Intervalo (segundos):"))
        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setMinimum(0.1)
        self.interval_spinbox.setMaximum(60.0)
        self.interval_spinbox.setSingleStep(0.1)
        self.interval_spinbox.setValue(DEFAULT_INTERVAL_SEC)
        interval_layout.addWidget(self.interval_spinbox)
        cycle_mode_layout.addLayout(interval_layout)

        cycle_buttons_layout = QHBoxLayout()
        self.start_cycle_button = QPushButton("Iniciar Ciclos")
        self.start_cycle_button.clicked.connect(self.start_cycles)
        cycle_buttons_layout.addWidget(self.start_cycle_button)

        self.stop_cycle_button = QPushButton("Detener Ciclos")
        self.stop_cycle_button.clicked.connect(self.stop_cycles)
        self.stop_cycle_button.setEnabled(False)
        cycle_buttons_layout.addWidget(self.stop_cycle_button)
        cycle_mode_layout.addLayout(cycle_buttons_layout)

        cycle_mode_group.setLayout(cycle_mode_layout)
        control_column_layout.addWidget(cycle_mode_group)

        control_column_layout.addStretch(1)

        center_layout.addLayout(control_column_layout, 1)

        main_layout.addLayout(center_layout)

        self.setLayout(main_layout)
        self.update_control_states(False, False)

    def populate_ports(self):
        self.port_selector.clear()
        ports = list_available_ports()
        if not ports:
            self.statusBar.showMessage("No se encontraron puertos COM disponibles.")
        else:
            for p in ports:
                self.port_selector.addItem(p)
            self.statusBar.showMessage("Puertos actualizados.")

    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.stop_cycles()
            self.stop_logging()

            if self.data_request_timer.isActive():
                self.data_request_timer.stop()

            self.serial_thread.stop()
            self.serial_thread = None
            self.is_connected = False

            self.connect_button.setText("Conectar")
            self.statusBar.showMessage("Desconectado.")
            self.temperature_display.setText("---.-- °C")
            self.elapsed_time_display.setText("0.00 s")

            self.time_data.clear()
            self.temp_data.clear()
            self.update_plot()
            self.start_time = None

            self.update_control_states(False, False)

        else:
            selected_port = self.port_selector.currentText()
            if not selected_port:
                self.statusBar.showMessage("Selecciona un puerto COM válido.")
                return

            self.start_time = None

            self.serial_thread = SerialReader(selected_port)
            self.serial_thread.temperature_received.connect(self.update_temperature_display)
            self.serial_thread.connection_status.connect(self.handle_connection_status)
            self.serial_thread.error_message.connect(self.statusBar.showMessage)

            self.serial_thread.start()
            self.connect_button.setText("Desconectando...")

    def request_temperature_from_arduino(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.request_data()
        else:
            if self.data_request_timer.isActive():
                self.data_request_timer.stop()

    def update_temperature_display(self, temp_value):
        try:
            self.temperature_display.setText(f"{temp_value:.2f} °C")

            if self.start_time is None:
                self.start_time = time.time()

            current_time = time.time() - self.start_time
            self.time_data.append(current_time)
            self.temp_data.append(temp_value)

            self.update_plot()
            self.elapsed_time_display.setText(f"{current_time:.2f} s")

            if self.is_logging:
                if self.csv_writer:
                    self.csv_writer.writerow([f"{current_time:.2f}", f"{temp_value:.2f}", self.current_servo_state])

        except Exception as e:
            self.statusBar.showMessage(f"Error al procesar datos o escribir CSV: {e}")

    def update_plot(self):
        if self.time_data and self.temp_data:
            self.line.set_data(list(self.time_data), list(self.temp_data))
            self.ax.relim()
            self.ax.autoscale_view()

        self.canvas.draw()

    def handle_connection_status(self, is_connected, message=""):
        self.is_connected = is_connected
        if is_connected:
            self.connect_button.setText("Desconectar")
            self.statusBar.showMessage(message)
            self.update_control_states(True, False)
            self.data_request_timer.start()
        else:
            self.connect_button.setText("Conectar")
            self.statusBar.showMessage(message)
            self.temperature_display.setText("---.-- °C")
            self.elapsed_time_display.setText("0.00 s")
            self.update_control_states(False, False)
            if self.serial_thread:
                self.serial_thread = None
            if self.data_request_timer.isActive():
                self.data_request_timer.stop()

    def send_open_command(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.send_command(COMMAND_SERVO_OPEN)
            self.current_servo_state = "Abierto"
            self.statusBar.showMessage("Comando: Abrir Servo")
        else:
            self.statusBar.showMessage("Error: No conectado al Arduino.")

    def send_close_command(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.send_command(COMMAND_SERVO_CLOSE)
            self.current_servo_state = "Cerrado"
            self.statusBar.showMessage("Comando: Cerrar Servo")
        else:
            self.statusBar.showMessage("Error: No conectado al Arduino.")

    def start_logging(self):
        if not self.is_connected:
            self.statusBar.showMessage("Error: Conecta el Arduino antes de iniciar el registro.")
            return

        if self.is_logging:
            self.statusBar.showMessage("El registro ya está activo.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"temperatura_registro_{timestamp}.csv"

        csv_filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Registro de Temperatura",
            default_filename,
            CSV_FILE_FILTER
        )

        if not csv_filename:
            self.statusBar.showMessage("Operación de guardado cancelada.")
            return

        try:
            self.csv_file = open(csv_filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(CSV_HEADERS)
            self.is_logging = True
            self.start_time = time.time()

            self.time_data.clear()
            self.temp_data.clear()
            self.update_plot()

            self.update_control_states(self.is_connected, self.cycle_timer.isActive())

            duration = self.logging_duration_spinbox.value()
            if duration > 0.0:
                self.manual_logging_timer.start(int(duration * 1000))
                self.statusBar.showMessage(f"Grabando en {os.path.basename(csv_filename)} por {duration:.1f} segundos.")
            else:
                self.statusBar.showMessage(f"Grabando en {os.path.basename(csv_filename)} (registro manual ilimitado).")

        except IOError as e:
            self.statusBar.showMessage(f"Error al crear archivo CSV: {e}")
            self.is_logging = False

    def stop_logging(self):
        if not self.is_logging:
            self.statusBar.showMessage("El registro de datos no está activo.")
            return

        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.is_logging = False
            self.logging_started_by_cycle = False
            self.statusBar.showMessage("Registro de datos detenido y archivo CSV cerrado.")
            self.elapsed_time_display.setText("0.00 s")
            self.update_control_states(self.is_connected, self.cycle_timer.isActive())

            if self.manual_logging_timer.isActive():
                self.manual_logging_timer.stop()

    def auto_stop_logging(self):
        if self.is_logging and not self.logging_started_by_cycle:
            self.statusBar.showMessage("Tiempo de registro manual finalizado. Deteniendo el registro de datos.")
            self.stop_logging()

    def start_cycles(self):
        if not self.is_connected:
            self.statusBar.showMessage("Error: Conecta el Arduino primero para iniciar ciclos.")
            return

        if self.cycle_timer.isActive():
            self.statusBar.showMessage("Los ciclos ya están en curso.")
            return

        self.total_cycles = self.cycle_spinbox.value()
        self.interval_duration = self.interval_spinbox.value()
        self.current_cycle = 0
        self.cycle_step = 0

        if not self.is_logging:
            self.logging_started_by_cycle = True
            prev_duration_setting = self.logging_duration_spinbox.value()
            self.logging_duration_spinbox.setValue(0.0)

            self.start_logging()

            self.logging_duration_spinbox.setValue(prev_duration_setting)

            if not self.is_logging:
                self.statusBar.showMessage("Error: No se pudo iniciar el registro de datos. Ciclos cancelados.")
                self.logging_started_by_cycle = False
                return

        else:
            self.logging_started_by_cycle = False

        self.statusBar.showMessage(f"Iniciando {self.total_cycles} ciclos con intervalo de {self.interval_duration:.1f}s.")
        self.update_control_states(self.is_connected, True)

        self.run_cycle_step()

    def stop_cycles(self):
        if not self.cycle_timer.isActive():
            return

        self.cycle_timer.stop()
        self.statusBar.showMessage("Modo de ciclos detenido.")
        self.current_cycle = 0

        if self.logging_started_by_cycle and self.is_logging:
            self.stop_logging()
        elif not self.logging_started_by_cycle and self.is_logging:
            self.statusBar.showMessage("Modo de ciclos detenido. El registro de datos continúa.")

        self.update_control_states(self.is_connected, False)

    def run_cycle_step(self):
        if self.current_cycle >= self.total_cycles:
            self.statusBar.showMessage(f"Ciclos completados ({self.total_cycles}).")
            self.stop_cycles()
            return

        if self.cycle_step == 0:
            self.send_open_command()
            self.statusBar.showMessage(f"Ciclo {self.current_cycle + 1}/{self.total_cycles}: Abriendo servo. Esperando {self.interval_duration:.1f}s...")
            self.cycle_timer.start(int(self.interval_duration * 1000))
            self.cycle_step = 1
        elif self.cycle_step == 1:
            self.send_close_command()
            self.statusBar.showMessage(f"Ciclo {self.current_cycle + 1}/{self.total_cycles}: Cerrando servo. Esperando {self.interval_duration:.1f}s...")
            self.cycle_timer.start(int(self.interval_duration * 1000))
            self.cycle_step = 2
        elif self.cycle_step == 2:
            self.current_cycle += 1
            if self.current_cycle < self.total_cycles:
                self.statusBar.showMessage(f"Ciclo {self.current_cycle}/{self.total_cycles} completado. Preparando siguiente.")
                self.cycle_step = 0
                self.run_cycle_step()
            else:
                self.statusBar.showMessage(f"Todos los ciclos completados ({self.total_cycles}).")
                self.stop_cycles()

    def update_control_states(self, is_connected, cycle_mode_active):
        self.port_selector.setEnabled(not is_connected)
        self.refresh_button.setEnabled(not is_connected)

        self.open_servo_button.setEnabled(is_connected and not cycle_mode_active)
        self.close_servo_button.setEnabled(is_connected and not cycle_mode_active)

        self.start_logging_button.setEnabled(is_connected and not cycle_mode_active and not self.is_logging)
        self.stop_logging_button.setEnabled(is_connected and self.is_logging)

        self.logging_duration_spinbox.setEnabled(is_connected and not self.is_logging and not cycle_mode_active)
        self.help_duration_button.setEnabled(is_connected and not self.is_logging and not cycle_mode_active)

        self.cycle_spinbox.setEnabled(is_connected and not cycle_mode_active and not self.is_logging)
        self.interval_spinbox.setEnabled(is_connected and not cycle_mode_active and not self.is_logging)
        self.start_cycle_button.setEnabled(is_connected and not cycle_mode_active and not self.is_logging)
        self.stop_cycle_button.setEnabled(is_connected and cycle_mode_active)

        if not is_connected:
            self.start_logging_button.setEnabled(False)
            self.stop_logging_button.setEnabled(False)
            self.open_servo_button.setEnabled(False)
            self.close_servo_button.setEnabled(False)
            self.cycle_spinbox.setEnabled(False)
            self.interval_spinbox.setEnabled(False)
            self.start_cycle_button.setEnabled(False)
            self.stop_cycle_button.setEnabled(False)
            self.logging_duration_spinbox.setEnabled(False)
            self.help_duration_button.setEnabled(False)

        if not is_connected or self.is_logging or cycle_mode_active:
            self.duration_help_label.hide()

    def toggle_duration_help_text(self):
        if self.duration_help_label.isHidden():
            self.duration_help_label.show()
        else:
            self.duration_help_label.hide()

    def closeEvent(self, event):
        self.stop_cycles()
        self.stop_logging()
        if self.data_request_timer.isActive():
            self.data_request_timer.stop()
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
        event.accept()
