import argparse
import os
import signal
import sys
import threading
from datetime import datetime
from queue import Queue
from time import sleep

import matplotlib
import matplotlib.animation as animation
import serial
from matplotlib import pyplot as plt

from snolog_parser import append_snolog_to_csv, create_snolog_csv, parse_raw_snolog

NUS_USA = "!USA\r".encode("utf-8")

interrupted = False


def sigint_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) to terminate the program gracefully.

    Sets a global flag to signal termination. The second SIGINT will
    exit immediately without waiting for the thread to finish.

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


def trigger_lidar_conversion(serial_port):
    """Trigger a lidar measurement on the device.

    Sends the !USA to the serial port to initiate a measurement.

    Args:
        serial_port: The serial port object.
    """
    nbytes = serial_port.write(NUS_USA)
    if nbytes != 5:
        print("something went wrong...?")


def read_snolog(serial_port):
    """Read a SNOLog packet from the serial port.

    Args:
        serial_port: The serial port object.

    Returns:
        snolog: The raw SNOLog data read from the port.
    """
    snolog = serial_port.read(128)

    return snolog


def lidar_control(serial_port, csv_filename, measurement_interval, read_delay, queue):
    """Control the lidar measurement and data logging.

    Runs in a separate thread to handle serial communication, data parsing,
    and CSV logging. Sends timestamp and distance data to the main thread for plotting.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
        measurement_interval: Seconds between measurements.
        read_delay: Delay before reading after triggering a measurement.
        queue: A thread-safe queue to pass data to the main thread.
    """
    global interrupted

    serial_port = serial.Serial(port=serial_port, baudrate=19200)

    create_snolog_csv(csv_filename)

    while not interrupted:
        trigger_lidar_conversion(serial_port)

        sleep(read_delay)
        raw_snolog = read_snolog(serial_port)
        # print(raw_snolog)

        snolog = parse_raw_snolog(raw_snolog)
        print(snolog)

        append_snolog_to_csv(csv_filename, snolog)

        # Send timestampe and distance data back to the main thread for plotting
        queue.put(snolog.unix_time)
        queue.put(snolog.lidar_tc_distance)

        sleep(measurement_interval - read_delay)

    serial_port.close()


def main(serial_port, csv_filename, measurement_interval=30, read_delay=0):
    """Main entry point for the application.

    Sets up signal handling, starts the lidar control thread, and initializes
    the real-time plotting interface.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
        measurement_interval: Seconds between measurements.
        read_delay: Delay before reading after triggering a measurement.
    """
    global interrupted

    signal.signal(signal.SIGINT, sigint_handler)

    queue = Queue(maxsize=2)

    lidar_control_thread = threading.Thread(
        target=lidar_control,
        args=(
            serial_port,
            csv_filename,
            measurement_interval,
            read_delay,
            queue,
        ),
    )
    lidar_control_thread.start()

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
        if queue.full():
            timestamp = queue.get()
            distance = queue.get()

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
    lidar_control_thread.join()
    sys.exit(0)


def parse_args():
    """Parse command-line arguments.

    Returns:
        args: Parsed arguments with the following attributes:
            - serial_port: Serial port device (e.g., "/dev/ttyUSB0").
            - csv: Path to the output CSV file.
            - measurement_interval: Time (seconds) between measurements.
            - read_delay: Delay (seconds) before reading snolog data after triggering a measurement.
    """
    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 snolog data logger",
        description="Manually trigger lidar measurements at a specified interval, then log and plot snolog data. This program is designed for SNOdars that are configured in 'manual' mode.",
    )

    parser.add_argument(
        "serial_port", help="Serial port number, e.g., /dev/ttyUSB0, COM7"
    )
    parser.add_argument("csv", help="Output CSV file name")
    parser.add_argument(
        "--measurement-interval",
        type=int,
        default=30,
        help="How often to take measurements. Default = 30 seconds",
    )
    parser.add_argument(
        "--read-delay",
        type=int,
        default=0,
        help="How long to wait before reading snolog data after triggering a measurement. Default = 0 seconds",
    )

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()

    main(
        serial_port=args.serial_port,
        csv_filename=args.csv,
        measurement_interval=args.measurement_interval,
        read_delay=args.read_delay,
    )
