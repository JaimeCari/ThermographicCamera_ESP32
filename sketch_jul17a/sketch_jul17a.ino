#include "max6675.h"

// Define los pines a los que conectaste el MAX6675
int SO_PIN = 10;   // Pin de datos del MAX6675 (SO/DO)
int CS_PIN = 11;   // Pin Chip Select del MAX6675 (CS/SS)
int SCK_PIN = 12;  // Pin Clock del MAX6675 (SCK/CLK)

// Crea una instancia del objeto MAX6675
MAX6675 termocupla(SCK_PIN, CS_PIN, SO_PIN);

void setup() {
  Serial.begin(9600); // Inicia comunicación serial con la PC
  Serial.println("Arduino listo para recibir comandos.");
  delay(500); // Pequeña espera para estabilización
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read(); // Lee el comando de Python

    if (command == 'T') {
      // Lee la temperatura en Celsius
      double temperaturaC = termocupla.readCelsius();

      // Verifica si la lectura es válida (MAX6675 devuelve NaN si hay error)
      if (isnan(temperaturaC)) {
        Serial.println("Error de lectura de termocupla!");
      } else {
        // Envía la temperatura como una cadena de texto con 2 decimales, seguida de un salto de línea
        Serial.print(temperaturaC, 2); // '2' para 2 decimales
        Serial.println(); // Salto de línea para indicar fin de mensaje
      }
    }
    // Aquí puedes añadir más 'else if' para otros comandos (ej. configurar LEDs, etc.)
  }
}