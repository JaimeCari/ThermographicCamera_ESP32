import numpy as np
import matplotlib.pyplot as plt
import pandas as pd # Usaremos pandas para cargar el CSV fácilmente
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# --- Parte 1: Cargar el Archivo CSV ---
def load_csv_data():
    """Permite al usuario seleccionar un archivo CSV y carga los datos de tiempo y temperatura."""
    root = tk.Tk()
    root.withdraw() # Ocultar la ventana principal de Tkinter

    file_path = filedialog.askopenfilename(
        title="Seleccionar archivo CSV de temperatura",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
    )

    if not file_path:
        print("No se seleccionó ningún archivo.")
        return None, None, None

    try:
        # Cargar el CSV usando pandas
        # Asegúrate que las columnas se llamen 'Tiempo (s)' y 'Temperatura (°C)'
        df = pd.read_csv(file_path)
        
        # Renombrar columnas para facilitar el acceso (opcional, pero buena práctica)
        df.columns = ['Tiempo_s', 'Temperatura_C']

        # Obtener los datos
        tiempo_s = df['Tiempo_s'].values
        temperatura_c = df['Temperatura_C'].values

        print(f"Archivo cargado: {file_path}")
        print(f"Número de puntos de datos: {len(tiempo_s)}")
        
        return tiempo_s, temperatura_c, file_path

    except Exception as e:
        print(f"Error al cargar el archivo CSV: {e}")
        return None, None, None

# --- Parte 2: Realizar la DFT y Graficar ---
def plot_dft(tiempo_s, temperatura_c, file_path):
    """
    Realiza la DFT sobre los datos de temperatura y los grafica.
    
    Args:
        tiempo_s (numpy.array): Array de tiempos en segundos.
        temperatura_c (numpy.array): Array de temperaturas en grados Celsius.
        file_path (str): Ruta del archivo CSV cargado.
    """
    if tiempo_s is None or temperatura_c is None:
        print("Datos no disponibles para graficar DFT.")
        return

    N = len(temperatura_c) # Número total de puntos de datos

    if N < 2:
        print("Se necesitan al menos 2 puntos de datos para calcular la DFT.")
        return

    # Calcular el período de muestreo (asumimos intervalos uniformes)
    # Si tus tiempos están en 0.2, 0.4, 0.6, etc., el periodo es 0.2
    Ts = tiempo_s[1] - tiempo_s[0] # Periodo de muestreo en segundos
    Fs = 1 / Ts # Frecuencia de muestreo en Hz (muestras por segundo)

    print(f"Periodo de muestreo (Ts): {Ts:.3f} s")
    print(f"Frecuencia de muestreo (Fs): {Fs:.3f} Hz")
    print(f"Frecuencia de Nyquist (Fs/2): {Fs/2:.3f} Hz (máxima frecuencia detectable)")

    # Realizar la Transformada Rápida de Fourier (FFT)
    # fft.fft calcula la DFT para números complejos
    # fft.rfft es más eficiente para entradas reales (como la nuestra)
    Y = np.fft.rfft(temperatura_c) 
    
    # Calcular las frecuencias correspondientes a los componentes de la FFT
    # fft.rfftfreq genera las frecuencias para rfft
    frecuencias = np.fft.rfftfreq(N, d=Ts) # d es el periodo de muestreo

    # Calcular la amplitud (magnitud) de cada componente de frecuencia
    # Multiplicamos por 2/N para obtener la amplitud correcta de la señal original
    # (excepto para el componente DC y la frecuencia de Nyquist si N es par)
    amplitudes = 2.0 / N * np.abs(Y)
    
    # El primer componente (frecuencia 0 Hz) es el valor DC (offset promedio)
    # No lo multiplicamos por 2, ya que no es una componente simétrica
    amplitudes[0] = np.abs(Y[0]) / N 

    # --- Graficar los resultados ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f'Análisis de Datos de Temperatura del CSV: {os.path.basename(file_path)}', fontsize=16)

    # Gráfica de la señal de tiempo original
    ax1.plot(tiempo_s, temperatura_c, marker='.', linestyle='-', markersize=4)
    ax1.set_title('Temperatura vs. Tiempo (Dominio del Tiempo)')
    ax1.set_xlabel('Tiempo (s)')
    ax1.set_ylabel('Temperatura (°C)')
    ax1.grid(True)

    # Gráfica del espectro de amplitud (Dominio de la Frecuencia)
    # Solo mostramos hasta la frecuencia de Nyquist (que es lo que rfftfreq ya hace)
    ax2.plot(frecuencias, amplitudes, marker='o', linestyle='-', markersize=4)
    ax2.set_title('Espectro de Amplitud (Dominio de la Frecuencia)')
    ax2.set_xlabel('Frecuencia (Hz)')
    ax2.set_ylabel('Amplitud (°C)')
    ax2.grid(True)
    ax2.set_xlim(0, Fs / 2) # Asegurarse de que el eje X vaya hasta la frecuencia de Nyquist

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajustar layout para el supertítulo
    plt.show()

# --- Ejecutar el análisis ---
if __name__ == "__main__":
    tiempo, temperatura, loaded_file_path = load_csv_data()
    plot_dft(tiempo, temperatura, loaded_file_path)