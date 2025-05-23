import serial
import pandas as pd
import matplotlib
import matplotlib.animation as animation
from datetime import datetime
from matplotlib import pyplot as plt
from queue import Queue
import threading
import csv

FIELDNAMES=[
        "Time",
        "Current (mA)",
        "Voltage (V)",
        "NRF Temperature",
        "PCB Temperature",
        "IMU Temperature",
        "IMU Roll",
        "IMU Pitch",
        "IMU Yaw",
        "IMU Flag",
        "Lidar SoC Temperature",
        "Lidar PCB Temperature",
        "Lidar Distance",
        "Heater Enabled",
        "Outside Temperature",
        "Seasonal Snow Depth",
        "Seasonal Snow Fall",
        "New Snow Fall",
        "DoY SWE",
        "Temp SWE",
]

CSV_FILENAME='test.csv'

def create_csv_header(filename):
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')        
        writer.writerow(FIELDNAMES)

def append_to_csv(filename, data):
    with open(filename, 'a') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')        
        writer.writerow(data)


def read_rs232_data(queue):
    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    while True:
        raw_bytes = serial_port.readline()

        csv_string = raw_bytes.decode()

        csv_list = csv_string.strip().split(",")

        data = [float(x) for x in csv_list]

        print(data)

        queue.put(data)

        append_to_csv(CSV_FILENAME, data)

    # TODO: graceful exit
    serial_port.close()


if __name__ == "__main__":

    create_csv_header(CSV_FILENAME)

# df = pd.DataFrame(
#     columns=[
#         "Time",
#         "Current (mA)",
#         "Voltage (V)",
#         "NRF Temperature",
#         "PCB Temperature",
#         "IMU Temperature",
#         "IMU Roll",
#         "IMU Pitch",
#         "IMU Yaw",
#         "IMU Flag",
#         "Lidar SoC Temperature",
#         "Lidar PCB Temperature",
#         "Lidar Distance",
#         "Heater Enabled",
#         "Outside Temperature",
#         "Seasonal Snow Depth",
#         "Seasonal Snow Fall",
#         "New Snow Fall",
#         "DoY SWE",
#         "Temp SWE",
#     ],
# )

    queue = Queue()

    rs232_thread = threading.Thread(target=read_rs232_data, args=(queue,))
    rs232_thread.start()

    fig, ax = plt.subplots()
    line, = ax.plot([], [], '-o')

    # Automatically format datetimes on the x-axis
    locator = matplotlib.dates.AutoDateLocator()
    formatter = matplotlib.dates.AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_tick_params(rotation=30)

    plt.xlabel("Time")
    plt.ylabel("Snow Depth (m)")

    # Add padding so the x-axis label doesn't get cut off due to the rotated
    # tick labels.
    plt.subplots_adjust(bottom=0.18)

    xdata = []
    ydata = []

    def fetch_data():
        if not queue.empty():
            data = queue.get()
            # TODO: enum instead of hardcoding
            timestamp = data[0] 
            snowdepth = data[15]

            yield timestamp, snowdepth
        else:
            yield None

    def update_plot(frame):
        if frame:
            timestamp = datetime.fromtimestamp(frame[0])
            snowdepth = frame[1]

            xdata.append(timestamp)
            ydata.append(snowdepth)

            line.set_data(xdata, ydata)

            # Automatically resize figure based upon data limits
            ax.relim()
            ax.autoscale_view()
            ax.figure.canvas.draw()
        
        return line,


    ani = animation.FuncAnimation(fig, update_plot, fetch_data, interval=30000, save_count=1000, blit=True)

    plt.show()

    # while True:
    #     if not queue.empty():
    #         print(queue.get())

