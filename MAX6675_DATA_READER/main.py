import sys
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QStatusBar, QFileDialog) # Import QFileDialog
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from collections import deque
import time
import csv
from datetime import datetime
import os # Import os for path manipulation

# --- Hilo para la comunicación serial (para no bloquear la GUI) ---
class SerialReader(QThread):
    temperature_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    error_message = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._running = True
        self.first_data_received = False

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connection_status.emit(True)
            self.error_message.emit("Conectado exitosamente.")
            self.first_data_received = False
        except serial.SerialException as e:
            self.error_message.emit(f"Error al conectar: {e}")
            self.connection_status.emit(False)
            self._running = False
            return

        while self._running:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.write(b'T') # Solicitar temperatura
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        if "Error" not in line:
                            self.temperature_received.emit(line)
                        else:
                            self.error_message.emit(f"Arduino: {line}")
                self.msleep(200) # This controls the data request frequency
            except serial.SerialException as e:
                self.error_message.emit(f"Error de comunicación serial: {e}")
                self._running = False
                self.connection_status.emit(False)
            except Exception as e:
                self.error_message.emit(f"Error inesperado en el hilo: {e}")
                self._running = False
                self.connection_status.emit(False)

        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connection_status.emit(False)
            self.error_message.emit("Conexión serial cerrada.")

    def stop(self):
        self._running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.wait()

# --- Clase principal de la aplicación GUI ---
class ArduinoControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        
        self.time_data = deque(maxlen=100)
        self.temp_data = deque(maxlen=100)
        self.start_time = None

        self.csv_file = None
        self.csv_writer = None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Control de Arduino Nano con MAX6675")
        self.setGeometry(100, 100, 800, 600)

        main_layout = QVBoxLayout()

        self.statusBar = QStatusBar()
        main_layout.addWidget(self.statusBar)
        self.statusBar.showMessage("Listo para conectar.")

        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Puerto COM:"))
        self.port_selector = QComboBox()
        self.populate_ports()
        connection_layout.addWidget(self.port_selector)
        
        self.refresh_button = QPushButton("Refrescar Puertos")
        self.refresh_button.clicked.connect(self.populate_ports)
        connection_layout.addWidget(self.refresh_button)

        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        
        main_layout.addLayout(connection_layout)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperatura Actual:"))
        
        self.temperature_display = QLabel("---.-- °C")
        self.temperature_display.setStyleSheet("font-size: 24px; font-weight: bold; color: blue;")
        temp_layout.addWidget(self.temperature_display)
        
        main_layout.addLayout(temp_layout)

        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)
        
        self.ax.set_title("Temperatura vs. Tiempo")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel("Temperatura (°C)")
        self.ax.grid(True)
        
        self.line, = self.ax.plot([], [], 'r-')
        self.figure.tight_layout()

        self.setLayout(main_layout)

    def populate_ports(self):
        self.port_selector.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_selector.addItem(p.device)
        if not ports:
            self.statusBar.showMessage("No se encontraron puertos COM disponibles.")
        else:
            self.statusBar.showMessage("Puertos actualizados.")

    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            # Disconnect
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_button.setText("Conectar")
            self.statusBar.showMessage("Desconectado.")
            self.temperature_display.setText("---.-- °C")
            
            # Clear plot and reset start_time
            self.time_data.clear()
            self.temp_data.clear()
            self.update_plot()
            self.start_time = None

            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
                self.statusBar.showMessage("Desconectado y archivo CSV cerrado.")

        else:
            # Connect
            selected_port = self.port_selector.currentText()
            if not selected_port:
                self.statusBar.showMessage("Selecciona un puerto COM válido.")
                return
            
            # --- NUEVO: Solicitar al usuario el nombre y ubicación del archivo ---
            # Get current timestamp for a default filename suggestion
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"temperatura_registro_{timestamp}.csv"
            
            # Open file dialog
            csv_filename, _ = QFileDialog.getSaveFileName(
                self, # Parent widget
                "Guardar Registro de Temperatura", # Dialog title
                default_filename, # Default filename suggestion
                "Archivos CSV (*.csv);;Todos los archivos (*.*)" # File filters
            )

            if not csv_filename: # If user canceled the dialog
                self.statusBar.showMessage("Operación de guardado cancelada.")
                return
            # --- FIN NUEVO ---

            try:
                # Use the filename provided by the user
                self.csv_file = open(csv_filename, 'w', newline='')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow(['Tiempo (s)', 'Temperatura (°C)'])
                self.statusBar.showMessage(f"Grabando en {os.path.basename(csv_filename)}") # Display only filename in status bar

            except IOError as e:
                self.statusBar.showMessage(f"Error al crear archivo CSV: {e}")
                return

            self.start_time = None # Ensure start_time is None before starting thread

            self.serial_thread = SerialReader(selected_port, 9600)
            self.serial_thread.temperature_received.connect(self.update_temperature_display)
            self.serial_thread.connection_status.connect(self.handle_connection_status)
            self.serial_thread.error_message.connect(self.statusBar.showMessage)
            self.serial_thread.start()
            self.connect_button.setText("Desconectando...")

    def update_temperature_display(self, temp_str):
        """Actualiza la etiqueta de temperatura, los datos de la gráfica y el CSV."""
        try:
            temp_value = float(temp_str)
            self.temperature_display.setText(f"{temp_value:.2f} °C")
            
            if self.start_time is None:
                self.start_time = time.time()
            
            current_time = time.time() - self.start_time
            self.time_data.append(current_time)
            self.temp_data.append(temp_value)
            
            self.update_plot()

            if self.csv_writer:
                self.csv_writer.writerow([f"{current_time:.2f}", f"{temp_value:.2f}"])

        except ValueError:
            self.temperature_display.setText("Inválido")
            self.statusBar.showMessage(f"Dato de temperatura inválido: {temp_str}")
        except Exception as e:
            self.statusBar.showMessage(f"Error al procesar datos o escribir CSV: {e}")

    def update_plot(self):
        """Redibuja la gráfica con los datos actuales."""
        if self.time_data and self.temp_data:
            self.line.set_data(list(self.time_data), list(self.temp_data))
            
            self.ax.relim()
            self.ax.autoscale_view()

        self.canvas.draw()

    def handle_connection_status(self, is_connected):
        """Actualiza la GUI según el estado de la conexión."""
        if is_connected:
            self.connect_button.setText("Desconectar")
            self.statusBar.showMessage("Conectado al Arduino y grabando datos.")
        else:
            self.connect_button.setText("Conectar")
            self.statusBar.showMessage("Desconectado del Arduino.")
            self.temperature_display.setText("---.-- °C")
            if self.serial_thread:
                self.serial_thread = None
            if self.csv_file: # Ensure CSV is closed if thread was terminated unexpectedly
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
                self.statusBar.showMessage("Desconectado y archivo CSV cerrado.")

    def closeEvent(self, event):
        """Se ejecuta cuando se cierra la ventana."""
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArduinoControlApp()
    window.show()
    sys.exit(app.exec_())