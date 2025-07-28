// Código para Arduino Nano para simular datos del sensor AMG8833
// Envía una matriz de 8x8 temperaturas aleatorias por el puerto serial
// SOLAMENTE cuando recibe el comando 'T' (seguido de un salto de línea) desde la terminal.
// Cada fila de la matriz se envía en una línea separada.

const int SENSOR_ROWS = 8;  // Filas de la matriz del sensor AMG8833
const int SENSOR_COLS = 8;  // Columnas de la matriz del sensor AMG8833
const long BAUD_RATE = 115200; // Velocidad de comunicación serial
const char* START_DATA_MARKER = "START DATA";
const char* END_DATA_MARKER = "END DATA";

float temperatureData[SENSOR_ROWS * SENSOR_COLS]; // Array plano para almacenar las temperaturas

void setup() {
  Serial.begin(BAUD_RATE);
  // Pequeña pausa para que el monitor serial se inicialice
  delay(1000); 
  Serial.println("Arduino Nano simulador de sensor AMG8833 iniciado.");
  Serial.println("Esperando comando 'T' para enviar datos...");
}

void loop() {
  // Solo genera y envía datos si se recibe el comando 'T'
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n'); // Lee hasta el salto de línea
    command.trim(); // Elimina espacios en blanco (incluido el salto de línea)

    if (command.equals("T")) {
      // Generar datos de temperatura simulados
      generateSimulatedTemperatureData();

      // Enviar el marcador de inicio
      Serial.println(START_DATA_MARKER);

      // Enviar los datos de temperatura, una fila por línea
      for (int r = 0; r < SENSOR_ROWS; r++) {
        for (int c = 0; c < SENSOR_COLS; c++) {
          int index = r * SENSOR_COLS + c;
          Serial.print(temperatureData[index], 2); // Imprimir con 2 decimales
          if (c < SENSOR_COLS - 1) {
            Serial.print(","); // Separador CSV dentro de la fila
          }
        }
        Serial.println(); // Salto de línea al final de cada fila
      }

      // Enviar el marcador de fin
      Serial.println(END_DATA_MARKER);

      // Pequeña pausa para simular el tiempo de muestreo del sensor real.
      // Ajusta este valor para controlar la velocidad de actualización.
      // 100 ms = 10 actualizaciones por segundo
      delay(100); 
    } else {
      Serial.println("Comando desconocido. Esperando 'T'.");
    }
  }
}

void generateSimulatedTemperatureData() {
  // Simula una matriz de temperaturas con un "punto caliente" que se mueve ligeramente
  // y un poco de ruido para que parezca más real.

  // Centro del "punto caliente" simulado, con un ligero desplazamiento aleatorio
  // Ajustamos el rango del random para el tamaño más pequeño
  int center_x = SENSOR_COLS / 2 + random(-SENSOR_COLS / 3, SENSOR_COLS / 3);
  int center_y = SENSOR_ROWS / 2 + random(-SENSOR_ROWS / 3, SENSOR_ROWS / 3);

  // Temperatura base y variaciones
  float base_temp = 25.0; // Temperatura ambiente base
  float hotspot_peak = 5.0 + (random(0, 100) / 100.0) * 3.0; // Pico de 5 a 8 grados sobre la base
  float noise_level = 0.3 + (random(0, 100) / 100.0) * 0.3; // Ruido de 0.3 a 0.6

  for (int r = 0; r < SENSOR_ROWS; r++) {
    for (int c = 0; c < SENSOR_COLS; c++) {
      int index = r * SENSOR_COLS + c;

      // Distancia al centro simulado
      float dist_x = c - center_x;
      float dist_y = r - center_y;
      float distance_sq = dist_x * dist_x + dist_y * dist_y;

      // Modelo de "punto caliente" gaussiano simple
      // Usa expf para float en Arduino
      // Ajustamos el divisor para un "punto caliente" más grande en una matriz pequeña
      float temp = base_temp + (hotspot_peak * expf(-distance_sq / (0.5f * (SENSOR_ROWS + SENSOR_COLS)))) + (random(-100, 100) / 100.0) * noise_level;

      // Asegurar que las temperaturas se mantengan dentro de un rango razonable
      if (temp < 20.0) temp = 20.0;
      if (temp > 40.0) temp = 40.0; // Rango más ajustado para 8x8 puede ser mejor

      temperatureData[index] = temp;
    }
  }
}