BAUD_RATE = 9600

COMMAND_REQUEST_TEMP = b'T'

COMMAND_SERVO_OPEN = b'O'
COMMAND_SERVO_CLOSE = b'C'

MAX_PLOT_POINTS = 100    

DATA_REQUEST_INTERVAL_MS = 200

APP_WINDOW_TITLE = "Monitor de Temperatura y Control de Servo"

TEMP_DISPLAY_STYLE = "font-size: 24px; font-weight: bold; color: red;"

CSV_HEADERS = ['Tiempo (s)', 'Temperatura (°C)', 'Estado Servo']

CSV_FILE_FILTER = "Archivos CSV (*.csv);;Todos los archivos (*.*)"

DEFAULT_CYCLE_COUNT = 5
DEFAULT_INTERVAL_SEC = 2.0
