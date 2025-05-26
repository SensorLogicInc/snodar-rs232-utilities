import serial
import argparse
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

def create_csv_header(filename):
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')        
        writer.writerow(FIELDNAMES)

def append_to_csv(filename, data):
    with open(filename, 'a') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')        
        writer.writerow(data)


def read_rs232_data(queue, csv_filename):
    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    while True:
        raw_bytes = serial_port.readline()

        csv_string = raw_bytes.decode()

        csv_list = csv_string.strip().split(",")

        data = [float(x) for x in csv_list]

        print(data)

        queue.put(data)

        append_to_csv(csv_filename, data)

    # TODO: graceful exit
    serial_port.close()


def main(csv_filename):

    create_csv_header(csv_filename)

    queue = Queue()

    rs232_thread = threading.Thread(target=read_rs232_data, args=(queue, csv_filename,))
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


    ani = animation.FuncAnimation(fig, update_plot, fetch_data, interval=5000, save_count=1000, blit=True)

    plt.show()


def parse_args():

    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 data logger",
        description="Log and plot ASCII data over RS232"
    )

    parser.add_argument('csv', help="CSV filename to log data to")

    args = parser.parse_args()

    return args

if __name__ == "__main__":

    args = parse_args()

    main(args.csv)

