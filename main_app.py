import sys
import csv
import time
import numpy as np
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer, QDateTime

from app_parameters import (
    BAUD_RATE, SENSOR_ROWS, SENSOR_COLS,
    GUI_UPDATE_INTERVAL_MS, CSV_FILENAME_PREFIX, CSV_HEADER, DEFAULT_SAVE_DIR,
    START_DATA_MARKER, END_DATA_MARKER
)
from serial_handler import SerialHandler
from app_gui import AppGUI

class MainApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.gui = AppGUI()
        self.serial_handler = SerialHandler()

        self.is_connected = False
        self.is_recording = False
        self.record_start_time = 0
        self.record_duration = 0
        self.csv_file = None
        self.csv_writer = None

        self._connect_signals()
        self._setup_timer()
        self._list_ports()
        self.gui.set_connection_buttons_state(self.is_connected)
        self.gui.set_record_buttons_state(self.is_recording)
        self.app.aboutToQuit.connect(self._on_app_quit)

    def _connect_signals(self):
        self.gui.connect_signal.connect(self._connect_serial)
        self.gui.disconnect_signal.connect(self._disconnect_serial)
        self.gui.start_record_signal.connect(self._start_recording)
        self.gui.stop_record_signal.connect(self._stop_recording)
        self.gui.select_file_signal.connect(self._open_file_dialog)

    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.setInterval(GUI_UPDATE_INTERVAL_MS)
        self.timer.timeout.connect(self._update_data)
        self.timer.start()

    def _list_ports(self):
        ports = self.serial_handler.list_available_ports()
        self.gui.update_port_list(ports)

    def _connect_serial(self, port):
        if self.serial_handler.connect(port):
            self.is_connected = True
            self.gui.set_connection_buttons_state(True)
            self.gui.show_message("Conexión Exitosa", f"Conectado a {port} correctamente.")
        else:
            self.is_connected = False
            self.gui.set_connection_buttons_state(False)
            self.gui.show_error("Error de Conexión", f"No se pudo conectar a {port}.")

    def _disconnect_serial(self):
        if self.is_connected:
            self.serial_handler.disconnect()
            self.is_connected = False
            self.gui.set_connection_buttons_state(False)
            self.gui.show_message("Desconexión Exitosa", "Puerto serial desconectado.")
            if self.is_recording:
                self._stop_recording()

    def _update_data(self):
        if self.is_connected:
            if isinstance(self.serial_handler, SerialHandler) and \
               self.serial_handler.ser and self.serial_handler.ser.is_open:
                try:
                    self.serial_handler.ser.write(b'T\n')
                except Exception as e:
                    print(f"Error al enviar comando 'T': {e}")
                    self._disconnect_serial()

            data = self.serial_handler.read_data()

            if data is not None:
                self.gui.update_heatmap(data)

                min_val = np.min(data)
                max_val = np.max(data)
                center_val = data[data.shape[0] // 2, data.shape[1] // 2]
                self.gui.update_stats(min_val, max_val, center_val)

                if self.is_recording:
                    self._write_to_csv(data)
                    if (time.time() - self.record_start_time) >= self.record_duration:
                        self._stop_recording()

    def _open_file_dialog(self):
        options = QFileDialog.Options()
        current_datetime = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        suggested_filename = f"{CSV_FILENAME_PREFIX}{current_datetime}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self.gui,
            "Guardar datos de temperatura como...",
            DEFAULT_SAVE_DIR if DEFAULT_SAVE_DIR else suggested_filename,
            "Archivos CSV (*.csv);;Todos los archivos (*.*)",
            options=options
        )
        if file_path:
            self.gui.set_save_path_display(file_path)
        else:
            self.gui.set_save_path_display("No seleccionado")

    def _start_recording(self, file_path, duration):
        if not self.is_connected:
            self.gui.show_error("Error de Registro", "Debes estar conectado al sensor para iniciar el registro.")
            return

        try:
            self.csv_file = open(file_path, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(CSV_HEADER)
            self.is_recording = True
            self.record_start_time = time.time()
            self.record_duration = duration
            self.gui.set_record_buttons_state(True)
            self.gui.show_message("Registro Iniciado", f"Grabando datos en: {file_path} por {duration} segundos.")
        except IOError as e:
            self.gui.show_error("Error de Archivo", f"No se pudo abrir el archivo para escritura: {e}")
            self.is_recording = False
            self.gui.set_record_buttons_state(False)

    def _write_to_csv(self, data):
        if self.csv_writer and self.csv_file:
            flat_data = data.flatten().tolist()
            self.csv_writer.writerow(flat_data)

    def _stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            self.gui.set_record_buttons_state(False)
            self.gui.show_message("Registro Detenido", "Registro de datos finalizado.")

    def _on_app_quit(self):
        print("Cerrando aplicación...")
        if self.is_connected:
            self._disconnect_serial()
        elif self.is_recording:
            self._stop_recording()

    def run(self):
        self.gui.show()
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    main_app = MainApp()
    main_app.run()
