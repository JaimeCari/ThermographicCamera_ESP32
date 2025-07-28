# Cámara Termográfica con MLX90640/AMG8833, ESP32 y PyQt

---

## Resumen del Proyecto

Este proyecto integra **sensores de cámara térmica MLX90640 o AMG8833** con un microcontrolador **ESP32** para capturar datos de temperatura en tiempo real. Una aplicación de escritorio desarrollada con **Python (PyQt)** visualiza estos datos como un mapa de calor dinámico y permite el registro de los mismos en archivos CSV.

Ideal para aplicaciones de monitoreo térmico, detección de puntos calientes, eficiencia energética y más, ofreciendo flexibilidad para diferentes resoluciones y necesidades de hardware.

---

## ✨ Características Principales

* **Soporte Multi-Sensor:** Compatible con sensores térmicos **MLX90640 (32x24 píxeles)** y **AMG8833 (8x8 píxeles)**.

* **Adquisición de Datos en Tiempo Real:** Captura de matriz de temperaturas desde el sensor seleccionado.

* **Comunicación Serial Fiable:** Conexión y desconexión automática al ESP32 a través de puertos seriales.

* **Visualización Interactiva:**

    * **Mapa de Calor:** Representación gráfica en tiempo real de las temperaturas usando `matplotlib` incrustado en PyQt.

    * **Estadísticas de Temperatura:** Muestra la temperatura mínima, máxima y central del sensor.

    * **Escala de Color Dinámica:** La escala de color del mapa de calor se ajusta automáticamente para resaltar los rangos de temperatura más relevantes.

* **Registro de Datos:**

    * Guardado de la matriz de temperaturas en archivos **CSV**.

    * Opción para especificar la duración de la grabación.

    * Selector de archivo intuitivo para guardar los logs.

* **Interfaz de Usuario Amigable (GUI):** Desarrollada con PyQt5, ofrece una experiencia de usuario clara y funcional.

---

## 🛠️ Tecnologías Utilizadas

* **Microcontrolador:** ESP32

* **Sensores:**

    * MLX90640 (Cámara Térmica Infrarroja 32x24 píxeles)

    * AMG8833 (Array de Sensor IR Térmico 8x8 píxeles)

* **Programación del ESP32:** Arduino IDE / PlatformIO (firmware incluido en las carpetas `AMG8833_esp32_config/` y `MLX90640_esp32_config/`).

* **Lenguaje de Programación (Aplicación de Escritorio):** Python 3.x

* **Librerías Python:**

    * `PyQt5`: Para la interfaz gráfica de usuario (GUI).

    * `pyserial`: Para la comunicación serial entre Python y el ESP32.

    * `numpy`: Para el procesamiento eficiente de las matrices de datos de temperatura.

    * `matplotlib`: Para la visualización del mapa de calor.

---

## 🚀 Guía de Inicio Rápido

Sigue estos pasos para poner en marcha el proyecto en tu máquina.

### 1. Requisitos de Hardware

* Placa de desarrollo ESP32 (ej. ESP32 DevKitC).

* Sensor de cámara térmica MLX90640 **o** AMG8833.

* Cables jumper para las conexiones.

* Cable USB para programar el ESP32 y para la comunicación serial.

### 2. Configuración del Hardware (Conexiones)

Asegúrate de conectar el sensor seleccionado al ESP32 utilizando el protocolo I2C. Las conexiones típicas son:

* **Sensor SDA** $\rightarrow$ **ESP32 SDA** (GPIO 21, por defecto en muchos ESP32)

* **Sensor SCL** $\rightarrow$ **ESP32 SCL** (GPIO 22, por defecto en muchos ESP32)

* **Sensor VCC** $\rightarrow$ **ESP32 3.3V**

* **Sensor GND** $\rightarrow$ **ESP32 GND**

### 3. Firmware del ESP32

1.  Abre el código del firmware (ubicado en la carpeta `AMG8833_esp32_config/` **o** `MLX90640_esp32_config/`, según el sensor que vayas a usar) en tu **Arduino IDE** o **PlatformIO**.

2.  Asegúrate de tener instaladas las librerías necesarias para el sensor específico que uses (ej. `Adafruit MLX90640 Library` o `Adafruit AMG88xx Library`) y para el ESP32.

3.  **Verifica el `BAUD_RATE`**: El `baud_rate` configurado en el código de tu ESP32 (generalmente 115200) debe coincidir con el `BAUD_RATE` especificado en `app_parameters.py`.

4.  **Carga el código** a tu ESP32. Este firmware espera un comando `'T'` (seguido de un salto de línea) para enviar un nuevo fotograma de datos, enmarcado por los marcadores "START DATA" y "END DATA".

### 4. Configuración del Entorno Python

1.  **Clona el repositorio** (o descarga los archivos) en tu máquina local:
    ```bash
    git clone [https://github.com/tu_usuario/tu_repositorio.git](https://github.com/tu_usuario/tu_repositorio.git)
    cd tu_repositorio
    ```
    *(Ajusta `tu_usuario/tu_repositorio` a la ruta real de tu proyecto)*

2.  **Instala las dependencias** usando el archivo `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

### 5. Ejecutar la Aplicación de Escritorio

1.  Asegúrate de que tu ESP32 con el sensor esté conectado a tu computadora a través de USB.
2.  Con el entorno virtual activado, ejecuta el archivo principal de la aplicación:
    ```bash
    python main_app.py
    ```

La aplicación GUI debería iniciarse. Selecciona el puerto COM de tu ESP32 en el desplegable y haz clic en "Conectar". Verás el mapa de calor actualizándose en tiempo real.

---

## 📂 Estructura del Proyecto

    ```bash
    .
    ├── app_parameters.py
    ├── serial_handler.py
    ├── app_gui.py
    ├── main_app.py
    ├── requirements.txt
    ├── README.md
    ├── AMG8833_esp32_config/    
    │   └── (AMG8833_firmware.ino)
    └── MLX90640_esp32_config/   
        └── (MLX90640_firmware.ino)
    ```

## Recursos y Fuentes

1. https://github.com/sparkfun/SparkFun_MLX90640_Arduino_Example
2. https://github.com/adafruit/Adafruit_MLX90640/blob/master/examples/MLX90640_simpletest/MLX90640_simpletest.ino
3. https://how2electronics.com/diy-amg8833-thermal-camera-with-esp8266-ili9341/

## Nota Importante

Este es un proyecto de código abierto y libre uso. Se ha desarrollado con el objetivo de ser una herramienta didáctica y funcional. Ten en cuenta que algunas partes de este código han podido ser asistidas o generadas utilizando modelos de inteligencia artificial para acelerar el desarrollo y proporcionar soluciones eficientes. 