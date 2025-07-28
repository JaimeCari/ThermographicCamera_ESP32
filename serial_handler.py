import serial
import serial.tools.list_ports
import numpy as np
import time

from app_parameters import BAUD_RATE, SENSOR_ROWS, SENSOR_COLS, START_DATA_MARKER, END_DATA_MARKER

class SerialHandler:
    def __init__(self):
        self.ser = None
        self.connected_port = None
        self.latest_data = None
        self.is_reading = False

    @staticmethod
    def list_available_ports():
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port):
        if self.ser and self.ser.is_open:
            self.disconnect()
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=BAUD_RATE,
                timeout=1
            )
            time.sleep(2)
            if self.ser.is_open:
                self.connected_port = port
                self.is_reading = True
                print(f"Conexión serial establecida en {port} a {BAUD_RATE} baudios.")
                return True
            else:
                print(f"No se pudo abrir el puerto {port}.")
                return False
        except serial.SerialException as e:
            print(f"Error al conectar al puerto serial {port}: {e}")
            self.connected_port = None
            self.is_reading = False
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.is_reading = False
            self.ser.close()
            print(f"Conexión serial en {self.connected_port} cerrada.")
            self.connected_port = None
        else:
            print("No hay conexión serial activa para cerrar.")

    def read_data(self):
        if not self.ser or not self.ser.is_open or not self.is_reading:
            return None

        data_buffer = []
        in_data_block = False
        start_time = time.time()
        max_wait_time = 5

        while (time.time() - start_time) < max_wait_time:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()

                    if line == START_DATA_MARKER:
                        in_data_block = True
                        data_buffer = []
                        continue

                    if line == END_DATA_MARKER:
                        if in_data_block:
                            in_data_block = False
                            if len(data_buffer) == SENSOR_ROWS:
                                try:
                                    temp_matrix = []
                                    for row_str in data_buffer:
                                        temp_matrix.append([float(x) for x in row_str.split(',')])
                                    if all(len(row) == SENSOR_COLS for row in temp_matrix):
                                        temp_array = np.array(temp_matrix, dtype=np.float32)
                                        self.latest_data = temp_array
                                        return temp_array
                                    else:
                                        print(f"Error: Fila con número incorrecto de columnas. Esperado {SENSOR_COLS}.")
                                        return None
                                except ValueError as ve:
                                    print(f"Error al convertir datos a flotante: {ve}")
                                    return None
                            else:
                                print(f"Error: Número de filas incorrecto. Esperado {SENSOR_ROWS}, Recibido {len(data_buffer)}.")
                                return None
                        continue

                    if in_data_block:
                        data_buffer.append(line)

            except serial.SerialException as e:
                print(f"Error de lectura serial: {e}")
                self.disconnect()
                return None
            except UnicodeDecodeError as e:
                print(f"Error de decodificación Unicode: {e}. Ignorando línea.")

        return None

    def get_latest_data(self):
        return self.latest_data

if __name__ == "__main__":
    handler = SerialHandler()
    ports = handler.list_available_ports()

    if not ports:
        print("No se encontraron puertos seriales disponibles.")
    else:
        print("Puertos seriales disponibles:", ports)
        chosen_port = ports[0]
        if handler.connect(chosen_port):
            print(f"Intentando leer datos del sensor desde {chosen_port}...")
            for i in range(5):
                data = handler.read_data()
                if data is not None:
                    print(f"\n--- Paquete {i+1} Recibido ---")
                    print("Dimensiones:", data.shape)
                    print("Min Temp:", np.min(data))
                    print("Max Temp:", np.max(data))
                else:
                    print(f"Esperando datos (paquete {i+1})...")
                time.sleep(1)
            handler.disconnect()
        else:
            print("No se pudo conectar al puerto seleccionado.")
