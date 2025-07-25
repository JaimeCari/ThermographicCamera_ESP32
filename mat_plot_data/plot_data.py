import pandas as pd
import matplotlib.pyplot as plt

def plot_temperature_data(file_path):
    try:
        df = pd.read_csv(file_path)

        # Ensure the required columns exist
        if 'Tiempo' not in df.columns or 'Temperatura' not in df.columns:
            print("Error: The CSV file must contain 'Tiempo' and 'Temperatura' columns.")
            return


        # Create the plot
        plt.figure(figsize=(10, 6)) # Adjust figure size as needed
        plt.plot(df['Tiempo'], df['Temperatura'], linestyle='-')

        # Add labels and title
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Temperatura (°C)')
        plt.title('Gráfico de Tiempo vs. Temperatura')
        plt.grid(True) 
          # Adjust y-axis limits as needed
        plt.tight_layout() 

        plt.show()

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    csv_file_path = 'data_water_21_07.csv'
    plot_temperature_data(csv_file_path)