"""Record ASCII SNOdar data via RS-232

This module implements a data logger for ASCII data received over RS-232 serial
communication. It logs data to CSV files and provides real-time visualization
using matplotlib.

This module assumes that the SNOdar sensor is configured in "snow depth" mode, has
RS-232 TX enabled in ASCII mode, and the unit is configured to make periodic measurements.

Usage:
    ```
    python rs232_ascii_data_logger.py COM3 output.csv
    ```
"""

import argparse
import csv
import os
import signal
import sys
import threading
from datetime import datetime
from queue import Queue

import matplotlib
import matplotlib.animation as animation
import serial
from matplotlib import pyplot as plt

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
    """Handle SIGINT (Ctrl+C) to terminate the program gracefully.

    The second SIGINT will exit immediately without waiting for the thread to finish.

    Args:
        sig: The signal number.
        frame: The current stack frame (unused).
    """
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
    """Create a csv file to save ASCII log data to.

    This only creates the file and writes the CSV header. Use
    `append_to_csv` to write data to the csv log file.

    Args:
        filename: The csv file name.
    """
    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile, dialect="excel")
        writer.writerow(FIELDNAMES)


def append_to_csv(filename, data):
    """Write a row of data to the csv file.

    This appends the data to the end of the given csv file.

    Args:
        filename: The csv file name.
        data: List of snolog data values.
    """
    with open(filename, "a") as csvfile:
        writer = csv.writer(csvfile, dialect="excel")
        writer.writerow(data)


def read_rs232_data(serial_port, csv_filename, queue):
    """Read ASCII data over RS-232.

    This function runs in a separate thread to allow the serial
    communication and plotting to co-exist nicely. The received data
    is sent to the main thread for plotting and saving.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
        queue: A thread-safe queue used to pass data to the main thread.
    """
    global interrupted
    serial_port = serial.Serial(port=serial_port, baudrate=19200)

    while not interrupted:
        # Read ASCII string from serial port
        raw_bytes = serial_port.readline()
        csv_string = raw_bytes.decode()

        # Convert string into list of numbers
        csv_list = csv_string.strip().split(",")
        data = [float(x) for x in csv_list]

        print(data)

        queue.put(data)

        append_to_csv(csv_filename, data)

    serial_port.close()


def main(serial_port, csv_filename):
    """Main entry point for the application.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
    """
    global interrupted

    signal.signal(signal.SIGINT, sigint_handler)

    create_csv_header(csv_filename)

    queue = Queue()

    rs232_thread = threading.Thread(
        target=read_rs232_data,
        args=(
            serial_port,
            csv_filename,
            queue,
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
    plt.ylabel("Distance (m)")

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
            distance = data[12]

            yield timestamp, distance
        else:
            yield None

    def update_plot(frame):
        if frame:
            timestamp = datetime.fromtimestamp(frame[0])
            distance = frame[1]

            xdata.append(timestamp)
            ydata.append(distance)

            line.set_data(xdata, ydata)

            # Automatically resize figure based upon data limits
            ax.relim()
            ax.autoscale_view()
            ax.figure.canvas.draw()

        return (line,)

    ani = animation.FuncAnimation(
        fig, update_plot, fetch_data, interval=1000, save_count=1000, blit=True
    )

    plt.show()

    # plt.show() is blocking, so this will never run until the plot window is closed
    # This will happen when sigint is sent or when the plot window is closed.
    # When the plot window is closed, the program will still keep running indefinitely
    # because the thread will never finish and join.
    rs232_thread.join()
    sys.exit(0)


def parse_args():
    """Parse command-line arguments

    Returns:
        args: Parsed arguments with the following attributes:
            - serial_port: Serial port device (e.g., "/dev/ttyUSB0").
            - csv: Path to the output CSV file.
    """
    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 ASCII data logger",
        description="Log and plot ASCII data over RS232",
    )

    parser.add_argument(
        "serial_port", help="Serial port number, e.g., /dev/ttyUSB0, COM7"
    )
    parser.add_argument("csv", help="CSV filename to log data to")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()

    main(args.serial_port, args.csv)
