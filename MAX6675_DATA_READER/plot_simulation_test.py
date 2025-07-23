import matplotlib.pyplot as plt
from collections import deque
from time import time, sleep
import random
from app_parameters import TEMP_SIM, MAX_PLOT_POINTS

def plot_temperature_data_simulation():  
    time_data = deque(maxlen = MAX_PLOT_POINTS)
    temperature_data = deque(maxlen=MAX_PLOT_POINTS)

    fig, ax = plt.subplots(figsize=(8, 6))
    line, = ax.plot(list(time_data), list(temperature_data), "r-")

    ax.set_title("Temperature vs. Time (Simulation)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(True)

    plt.ion()  
    plt.show(block = False)

    start_time = time()
    print("Starting data acquisition... Press Ctrl+C to stop.")

    try:
        for i in range(TEMP_SIM):
            simulated_temp = 20 + random.uniform(-2, 2) + (i / 50) * 0.5 
            current_time = time() - start_time
            time_data.append(current_time)
            temperature_data.append(simulated_temp)

            line.set_data(list(time_data), list(temperature_data))

            ax.relim()
            ax.autoscale_view()

            fig.canvas.draw()
            fig.canvas.flush_events()

            sleep(0.2)  

    except KeyboardInterrupt:
        print("Data acquisition stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        plt.ioff() 
        plt.close(fig)
        print("Plot closed.")

if __name__ == "__main__":
    plot_temperature_data()
