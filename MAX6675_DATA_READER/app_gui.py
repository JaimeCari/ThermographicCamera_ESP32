import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QStatusBar, QFileDialog,
                             QGroupBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from collections import deque
import time
import csv
from datetime import datetime
import os

from app_params import (
    MAX_PLOT_POINTS, APP_WINDOW_TITLE, TEMP_DISPLAY_STYLE,
    CSV_HEADERS, CSV_FILE_FILTER,
    COMMAND_SERVO_OPEN, COMMAND_SERVO_CLOSE,
    DEFAULT_CYCLE_COUNT, DEFAULT_INTERVAL_SEC
)
from serial_handler import SerialReader, list_available_ports

class ArduinoControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.current_servo_state = "Closed"
        self.time_data = deque(maxlen=MAX_PLOT_POINTS)
        self.temp_data = deque(maxlen=MAX_PLOT_POINTS)
        self.start_time = None

        self.csv_file = None
        self.csv_writer = None

        self.cycle_timer = QTimer()
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
        self.statusBar.showMessage("Ready to connect")

        top_layout = QHBoxLayout()

        connection_group = QGroupBox("Serial connection")
        connection_layout = QVBoxLayout()

        port_refresh_layout = QHBoxLayout()
        port_refresh_layout.addWidget(QLabel("COM Port:"))
        self.port_selector = QComboBox()
        self.populate_ports() 
        port_refresh_layout.addWidget(self.port_selector)
        
        self.refresh_button = QPushButton("Refresh ports")
        self.refresh_button.clicked.connect(self.populate_ports) 
        port_refresh_layout.addWidget(self.refresh_button)
        connection_layout.addLayout(port_refresh_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection) 
        connection_group.setLayout(connection_layout)
        top_layout.addWidget(connection_group)

        temp_group = QGroupBox("Current Temperature")
        temp_layout = QVBoxLayout()
        self.temperature_display = QLabel("---.-- °C")
        self.temperature_display.setStyleSheet(TEMP_DISPLAY_STYLE) # Estilo desde app_params
        temp_layout.addWidget(self.temperature_display, alignment=Qt.AlignCenter) # Centrar el texto
        temp_group.setLayout(temp_layout)
        top_layout.addWidget(temp_group)

        main_layout.addLayout(top_layout)
    
        center_layout = QHBoxLayout()

        
        plot_group = QGroupBox("Temperature Plot")
        plot_layout = QVBoxLayout()
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        
        self.ax.set_title("Temperature vs. Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (°C)")
        self.ax.grid(True)
        
        self.line, = self.ax.plot([], [], 'r-')
        self.figure.tight_layout()
        plot_group.setLayout(plot_layout)
        center_layout.addWidget(plot_group, 3) 

        control_column_layout = QVBoxLayout()

        manual_servo_group = QGroupBox("Manual Mode")
        manual_servo_layout = QVBoxLayout()
        self.open_servo_button = QPushButton("Open Servo (O)")
        self.open_servo_button.clicked.connect(self.send_open_command)
        manual_servo_layout.addWidget(self.open_servo_button)

        self.close_servo_button = QPushButton("Close Servo (C)")
        self.close_servo_button.clicked.connect(self.send_close_command)
        manual_servo_layout.addWidget(self.close_servo_button)
        manual_servo_group.setLayout(manual_servo_layout)
        control_column_layout.addWidget(manual_servo_group)

        cycle_mode_group = QGroupBox("Cycle Mode")
        cycle_mode_layout = QVBoxLayout()

        # Número de ciclos
        cycle_count_layout = QHBoxLayout()
        cycle_count_layout.addWidget(QLabel("Number of Cycles:"))
        self.cycle_spinbox = QSpinBox()
        self.cycle_spinbox.setMinimum(1)
        self.cycle_spinbox.setMaximum(1000)
        self.cycle_spinbox.setValue(DEFAULT_CYCLE_COUNT) 
        cycle_count_layout.addWidget(self.cycle_spinbox)
        cycle_mode_layout.addLayout(cycle_count_layout)

        # Duración del intervalo
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Duration of cycle (seconds):"))
        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setMinimum(0.1)
        self.interval_spinbox.setMaximum(60.0)
        self.interval_spinbox.setSingleStep(0.1)
        self.interval_spinbox.setValue(DEFAULT_INTERVAL_SEC) 
        interval_layout.addWidget(self.interval_spinbox)
        cycle_mode_layout.addLayout(interval_layout)

        cycle_buttons_layout = QHBoxLayout()
        self.start_cycle_button = QPushButton("Begin Cycles")
        self.start_cycle_button.clicked.connect(self.start_cycles)
        cycle_buttons_layout.addWidget(self.start_cycle_button)

        self.stop_cycle_button = QPushButton("Stop Cycles")
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
        self.update_control_states(False)

    def populate_ports(self):
        """Rellena el QComboBox con los puertos seriales disponibles."""
        self.port_selector.clear() # Limpia la lista actual de puertos
        ports = list_available_ports() # Usa la función de serial_handler
        if not ports:
            self.statusBar.showMessage("No se encontraron puertos COM disponibles.")
        else:
            for p in ports:
                self.port_selector.addItem(p)
            self.statusBar.showMessage("Puertos actualizados.")
    
    def toggle_connection(self):
        """Conecta o desconecta el hilo de comunicación serial."""
        if self.serial_thread and self.serial_thread.isRunning():
            # --- Lógica de Desconexión ---
            self.stop_cycles() # Asegura que los ciclos se detengan al desconectar
            self.serial_thread.stop() # Detiene el hilo
            self.serial_thread = None # Elimina la referencia al hilo
            self.connect_button.setText("Conectar")
            self.statusBar.showMessage("Desconectado.")
            self.temperature_display.setText("---.-- °C")
            self.update_control_states(False) # Deshabilita controles

            # Limpia los datos de la gráfica y la reinicia
            self.time_data.clear()
            self.temp_data.clear()
            self.update_plot()
            self.start_time = None # Reinicia el tiempo de inicio

            # Cierra el archivo CSV si está abierto
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
                self.statusBar.showMessage("Desconectado y archivo CSV cerrado.")

        else:
            # --- Lógica de Conexión ---
            selected_port = self.port_selector.currentText()
            if not selected_port:
                self.statusBar.showMessage("Selecciona un puerto COM válido.")
                return
            
            # --- Solicitar al usuario el nombre y ubicación del archivo CSV ---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"temperatura_registro_{timestamp}.csv"
            
            csv_filename, _ = QFileDialog.getSaveFileName(
                self, # Ventana padre
                "Guardar Registro de Temperatura", # Título del diálogo
                default_filename, # Nombre de archivo sugerido
                CSV_FILE_FILTER # Filtro de tipos de archivo desde app_params
            )

            if not csv_filename: # Si el usuario cancela el diálogo
                self.statusBar.showMessage("Operación de guardado cancelada.")
                return
            
            try:
                # Abre el archivo CSV para escritura
                self.csv_file = open(csv_filename, 'w', newline='')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow(CSV_HEADERS) # Escribe los encabezados desde app_params
                self.statusBar.showMessage(f"Grabando en {os.path.basename(csv_filename)}") # Muestra solo el nombre del archivo

            except IOError as e:
                self.statusBar.showMessage(f"Error al crear archivo CSV: {e}")
                return

            self.start_time = None # Asegura que el tiempo de inicio se resetee antes de la conexión

            # Crea e inicia el hilo SerialReader
            self.serial_thread = SerialReader(selected_port)
            # Conecta las señales del hilo a los slots de la GUI
            self.serial_thread.temperature_received.connect(self.update_temperature_display)
            self.serial_thread.connection_status.connect(self.handle_connection_status)
            self.serial_thread.error_message.connect(self.statusBar.showMessage)
            
            self.serial_thread.start() # Inicia la ejecución del hilo
            self.connect_button.setText("Desconectando...") # Texto temporal mientras se establece la conexión
    
    def update_temperature_display(self, temp_value):
        """Actualiza la etiqueta de temperatura, los datos de la gráfica y el CSV."""
        try:
            # Actualiza el QLabel de la temperatura
            self.temperature_display.setText(f"{temp_value:.2f} °C")
            
            # Si es la primera vez que se recibe un dato, registra el tiempo de inicio
            if self.start_time is None:
                self.start_time = time.time()
            
            current_time = time.time() - self.start_time # Calcula el tiempo transcurrido
            self.time_data.append(current_time) # Añade tiempo a la deque
            self.temp_data.append(temp_value) # Añade temperatura a la deque
            
            self.update_plot() # Llama a la función para redibujar la gráfica
    
            # Si el escritor CSV está activo, graba los datos
            if self.csv_writer:
                # Escribimos el tiempo, la temperatura y el estado actual del servo
                self.csv_writer.writerow([f"{current_time:.2f}", f"{temp_value:.2f}", self.current_servo_state])
    
        except Exception as e:
            self.statusBar.showMessage(f"Error al procesar datos o escribir CSV: {e}")
    
    def update_plot(self):
        """Redibuja la gráfica con los datos actuales."""
        if self.time_data and self.temp_data:
            # Actualiza los datos de la línea en la gráfica
            self.line.set_data(list(self.time_data), list(self.temp_data))
            
            # Recalcula los límites del eje y ajusta la vista
            self.ax.relim()
            self.ax.autoscale_view()
    
        self.canvas.draw() # Fuerza el redibujo del lienzo de Matplotlib
    
    def handle_connection_status(self, is_connected, message=""):
        """Actualiza la GUI según el estado de la conexión serial."""
        if is_connected:
            self.connect_button.setText("Desconectar")
            self.statusBar.showMessage(message) # Muestra el mensaje de conexión
            self.update_control_states(True) # Habilita controles
        else:
            self.connect_button.setText("Conectar")
            self.statusBar.showMessage(message) # Muestra el mensaje de desconexión/error
            self.temperature_display.setText("---.-- °C")
            self.update_control_states(False) # Deshabilita controles
            if self.serial_thread: # Si el hilo existía pero se desconectó
                self.serial_thread = None
            # Asegura que el CSV se cierre si la conexión se interrumpió inesperadamente
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
                self.statusBar.showMessage(f"{message} y archivo CSV cerrado.")

    # --- NUEVOS MÉTODOS PARA EL CONTROL MANUAL DEL SERVO ---
    def send_open_command(self):
        """Envía el comando para abrir el servo."""
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.send_command(COMMAND_SERVO_OPEN)
            self.current_servo_state = "Abierto" # Actualiza el estado para el CSV
            self.statusBar.showMessage("Comando: Abrir Servo")
        else:
            self.statusBar.showMessage("Error: No conectado al Arduino.")

    def send_close_command(self):
        """Envía el comando para cerrar el servo."""
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.send_command(COMMAND_SERVO_CLOSE)
            self.current_servo_state = "Cerrado" # Actualiza el estado para el CSV
            self.statusBar.showMessage("Comando: Cerrar Servo")
        else:
            self.statusBar.showMessage("Error: No conectado al Arduino.")

    # --- NUEVOS MÉTODOS PARA EL MODO DE CICLOS ---
    def start_cycles(self):
        """Inicia el modo de ciclos automáticos del servo."""
        if not (self.serial_thread and self.serial_thread.isRunning()):
            self.statusBar.showMessage("Error: Conecta el Arduino primero para iniciar ciclos.")
            return

        self.total_cycles = self.cycle_spinbox.value()
        self.interval_duration = self.interval_spinbox.value()
        self.current_cycle = 0
        self.cycle_step = 0 # Inicia en el paso de abrir el servo
        
        self.statusBar.showMessage(f"Iniciando {self.total_cycles} ciclos con intervalo de {self.interval_duration:.1f}s.")
        self.update_control_states(False, cycle_mode_active=True) # Deshabilita controles manuales, habilita detener ciclo
        
        # El primer paso se ejecuta inmediatamente, luego el timer toma el control
        self.run_cycle_step()

    def stop_cycles(self):
        """Detiene el modo de ciclos automáticos del servo."""
        self.cycle_timer.stop()
        self.statusBar.showMessage("Modo de ciclos detenido.")
        self.update_control_states(True, cycle_mode_active=False) # Habilita controles manuales, deshabilita detener ciclo
        self.current_cycle = 0 # Reinicia el contador de ciclos

    def run_cycle_step(self):
        """Ejecuta un paso del ciclo (abrir, esperar, cerrar, esperar)."""
        if self.current_cycle >= self.total_cycles:
            self.statusBar.showMessage(f"Ciclos completados ({self.total_cycles}).")
            self.stop_cycles()
            return

        if self.cycle_step == 0: # Paso 0: Abrir el servo
            self.send_open_command()
            self.statusBar.showMessage(f"Ciclo {self.current_cycle + 1}/{self.total_cycles}: Abriendo servo. Esperando {self.interval_duration:.1f}s...")
            self.cycle_timer.start(int(self.interval_duration * 1000)) # Espera el intervalo
            self.cycle_step = 1
        elif self.cycle_step == 1: # Paso 1: Esperar con el servo abierto, luego cerrar
            self.send_close_command()
            self.statusBar.showMessage(f"Ciclo {self.current_cycle + 1}/{self.total_cycles}: Cerrando servo. Esperando {self.interval_duration:.1f}s...")
            self.cycle_timer.start(int(self.interval_duration * 1000)) # Espera el intervalo
            self.cycle_step = 2
        elif self.cycle_step == 2: # Paso 2: Esperar con el servo cerrado, luego avanzar al siguiente ciclo
            self.current_cycle += 1
            if self.current_cycle < self.total_cycles:
                self.statusBar.showMessage(f"Ciclo {self.current_cycle}/{self.total_cycles} completado. Preparando siguiente.")
                self.cycle_step = 0 # Reinicia para el siguiente ciclo
                # No necesitamos un delay aquí, el siguiente paso se ejecutará en la próxima llamada del timer
                self.run_cycle_step() # Llama recursivamente para iniciar el siguiente ciclo inmediatamente
            else:
                self.statusBar.showMessage(f"Ciclos completados ({self.total_cycles}).")
                self.stop_cycles()

    def update_control_states(self, enable_manual_controls, cycle_mode_active=False):
        """Habilita/deshabilita los controles de la GUI."""
        # Controles manuales del servo
        self.open_servo_button.setEnabled(enable_manual_controls and not cycle_mode_active)
        self.close_servo_button.setEnabled(enable_manual_controls and not cycle_mode_active)

        # Controles del modo de ciclos
        self.cycle_spinbox.setEnabled(enable_manual_controls and not cycle_mode_active)
        self.interval_spinbox.setEnabled(enable_manual_controls and not cycle_mode_active)
        self.start_cycle_button.setEnabled(enable_manual_controls and not cycle_mode_active)
        self.stop_cycle_button.setEnabled(enable_manual_controls and cycle_mode_active)

    def closeEvent(self, event):
        """Se ejecuta cuando se intenta cerrar la ventana de la aplicación."""
        self.stop_cycles() # Asegura que los ciclos se detengan
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop() # Detiene el hilo de comunicación serial
        if self.csv_file:
            self.csv_file.close() # Cierra el archivo CSV
            self.csv_file = None
            self.csv_writer = None
        event.accept() # Acepta el evento de cierre (permite que la ventana se cierre)
    

