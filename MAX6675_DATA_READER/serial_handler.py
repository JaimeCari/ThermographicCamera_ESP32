import serial
import serial.tools.list_ports
import time
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
from app_params import BAUD_RATE, COMMAND_REQUEST_TEMP, DATA_REQUEST_INTERVAL_MS

class SerialReader(QThread):
    temperature_received = pyqtSignal(float)
    connection_status = pyqtSignal(bool, str)
    error_message = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.ser = None
        self.running = True
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.request_data)

    def run(self):
        try:
            self.ser = serial.Serial(self.port, baudrate=BAUD_RATE, timeout=1)
            time.sleep(2)
            if self.ser.is_open:
                self.connection_status.emit(True, f"Connected to port: {self.port}")
                print("SerialReader connected to port:", self.port)
                self.read_timer.start(DATA_REQUEST_INTERVAL_MS)
                self.exec_()
            else:
                self.connection_status.emit(False, f"Failed to open port: {self.port}")
                print("SerialReader failed to open port:", self.port)
        except serial.SerialException as e:
            self.connection_status.emit(False, f"Error connecting: {e}")
            self.error_message.emit(f"Serial port error: {e}")
            print(f"SerialReader: Serial port error: {e}")
        except Exception as e:
            self.connection_status.emit(False, f"Unexpected error: {e}")
            self.error_message.emit(f"Unexpected error in serial thread: {e}")
            print(f"SerialReader: Unexpected error: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("SerialReader: Serial port closed.")

    def request_data(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(COMMAND_REQUEST_TEMP)
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    try:
                        temp_value = float(line)
                        self.temperature_received.emit(temp_value)
                    except ValueError:
                        self.error_message.emit(f"Invalid temperature data received: '{line}'")
            except serial.SerialException as e:
                self.error_message.emit(f"Error reading from serial port: {e}")
                self.stop()
            except Exception as e:
                self.error_message.emit(f"Error processing serial data: {e}")
                self.stop()
                
    def send_command(self, command_bytes):
        """Sends a command (bytes) to the serial port."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(command_bytes)
                print(f"SerialReader: Command sent: {command_bytes}")
            except serial.SerialException as e:
                self.error_message.emit(f"Error sending command: {e}")
            except Exception as e:
                self.error_message.emit(f"Unexpected error sending command: {e}")
        else:
            self.error_message.emit("No active serial connection to send commands.")


    def stop(self):
        print("SerialReader: Requesting thread stop.")
        self.read_timer.stop()
        self.running = False
        self.quit()
        self.wait()
        print("SerialReader: Thread stopped.")

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No available serial ports found.")
        return []
    print("Available serial ports:")
    port_names = []
    for index, p in enumerate(ports):
        print(f"[{index}]: {p.device} - {p.description}")
        port_names.append(p.device)
    return port_names

def test_serial_communication_standalone():
    available_ports = list_available_ports()
    if not available_ports:
        return

    selected_port = None
    while selected_port is None:
        try:
            choice = input("Enter the number of the COM port to connect: ")
            port_index = int(choice)
            if 0 <= port_index < len(available_ports):
                selected_port = available_ports[port_index]
            else:
                print("Invalid port number. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    reader_thread = SerialReader(selected_port)
    reader_thread.temperature_received.connect(lambda temp: print(f"Temperature received: {temp:.2f}°C"))
    reader_thread.connection_status.connect(lambda status, msg: print(f"Connection status: {msg} (Status: {status})"))
    reader_thread.error_message.connect(lambda msg: print(f"ERROR: {msg}"))

    print("\nStarting SerialReader thread. Press Ctrl+C to stop.")
    reader_thread.start()

    try:
        while reader_thread.isRunning():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        if reader_thread.isRunning():
            reader_thread.stop()
        print("Serial communication test finished.")

if __name__ == "__main__":
    app = QApplication([])
    test_serial_communication_standalone()
    app.quit()
