import serial
import argparse
import threading
import csv
import signal
import sys
import os
import matplotlib
import matplotlib.animation as animation
from datetime import datetime
from matplotlib import pyplot as plt
from queue import Queue

FIELDNAMES = [
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

interrupted = False


def sigint_handler(sig, frame):
    global interrupted
    interrupted = True

    sigint_handler.sigint_count += 1

    if sigint_handler.sigint_count == 1:
        print("\nTerminating. Waiting to collect last data packet...")
        print("Send SIGINT again to terminate immediately")
    else:
        # use os._exit() to exit immediately without cleaning up and waiting for the thread to join.
        os._exit(1)


sigint_handler.sigint_count = 0


def create_csv_header(filename):
    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile, dialect="excel")
        writer.writerow(FIELDNAMES)


def append_to_csv(filename, data):
    with open(filename, "a") as csvfile:
        writer = csv.writer(csvfile, dialect="excel")
        writer.writerow(data)


def read_rs232_data(queue, csv_filename):
    global interrupted
    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    while not interrupted:
        raw_bytes = serial_port.readline()

        csv_string = raw_bytes.decode()

        csv_list = csv_string.strip().split(",")

        data = [float(x) for x in csv_list]

        print(data)

        queue.put(data)

        append_to_csv(csv_filename, data)

    serial_port.close()


def main(csv_filename):
    global interrupted

    signal.signal(signal.SIGINT, sigint_handler)

    create_csv_header(csv_filename)

    queue = Queue()

    rs232_thread = threading.Thread(
        target=read_rs232_data,
        args=(
            queue,
            csv_filename,
        ),
    )
    rs232_thread.start()

    fig, ax = plt.subplots()
    (line,) = ax.plot([], [], "-o")

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

        return (line,)

    ani = animation.FuncAnimation(
        fig, update_plot, fetch_data, interval=5000, save_count=1000, blit=True
    )

    plt.show()

    # plt.show() is blocking, so this will never run until the plot window is closed
    # This will happen when sigint is sent or when the plot window is closed.
    # When the plot window is closed, the program will still keep running indefinitely
    # because the thread will never finish and join.
    rs232_thread.join()
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 data logger",
        description="Log and plot ASCII data over RS232",
    )

    parser.add_argument("csv", help="CSV filename to log data to")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()

    main(args.csv)
