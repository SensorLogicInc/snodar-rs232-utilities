"""Trigger lidar measurements and capture the resulting snolog data via RS-232.

This module provides a CLI program for manually triggering lidar measurements
at a set interval and saving the snolog data to a csv. Distance data is plotted
in real-time.

This module assumes that the SNOdar sensor is configured in "manual" mode and has RS-232 TX enabled.

Usage:
    Basic usage (30-second measurement interval):
        ```
        python rs232_data_capture.py /dev/ttyUSB0 output.csv
        ```

    60-second measurement interval, waiting for 15 seconds after each
    measurement before reading the snolog via rs232:
        ```
        python rs232_data_capture.py --measurement-interval 60 --read-delay 15 COM4 output.csv
        ```

        Note that reading from the serial port is a blocking operation, so the code won't advance
        until 128 bytes have been read, regardless of what --read-delay is set to. --read-delay
        defaults to 0 since the serial port will keep waiting and reading until the SNOdar sends an
        entire snolog.
"""

import argparse
import os
import signal
import sys
import threading
from datetime import datetime
from queue import Queue
from time import sleep, time

import matplotlib
import matplotlib.animation as animation
import serial
from matplotlib import pyplot as plt

import snodar_live_health
from snolog_parser import append_snolog_to_csv, create_snolog_csv, parse_raw_snolog

# Don't let windows take focus when the plot updates.
plt.rcParams["figure.raise_window"] = False

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


def trigger_lidar_conversion(serial_port):
    """Trigger a lidar measurement on the device.

    This will send the !USA command to the serial port to initiate a measurement.

    Args:
        serial_port: The serial port object.
    """
    # Command for triggering a lidar measurement. The SNOdar expects commands to end with
    # a carriage return. Pyserial expects the string to be encoding as raw bytes, so
    # we encode it as a utf-8 string into a bytes object.
    NUS_USA = "!USA\r".encode("utf-8")

    nbytes = serial_port.write(NUS_USA)
    if nbytes != len(NUS_USA):
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


def lidar_control(
    serial_port, csv_filename, measurement_interval, read_delay, verbose, queue
):
    """Control the lidar measurement and data logging.

    This runs in a separate thread to handle serial communication, data parsing,
    and CSV logging. Timestamp and distance data are sent to the main thread for plotting.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
        measurement_interval: Seconds between measurements.
        read_delay: Delay before reading after triggering a measurement.
        queue: A thread-safe queue used to pass data to the main thread.
    """
    global interrupted

    serial_port = serial.Serial(port=serial_port, baudrate=19200)

    create_snolog_csv(csv_filename)

    while not interrupted:
        t_start = time()
        trigger_lidar_conversion(serial_port)

        sleep(read_delay)
        raw_snolog = read_snolog(serial_port)
        # print(raw_snolog)

        snolog = parse_raw_snolog(raw_snolog)
        if verbose:
            print(snolog)
            print()

        append_snolog_to_csv(csv_filename, snolog)

        health_flags = snodar_live_health.parse_flags(
            snolog.health_flags_hi, snolog.health_flags_lo
        )
        if verbose:
            print(health_flags)
            print()

        # Print warnings if any of the flags indicate a sensor health error
        snodar_live_health.check_flags(health_flags)

        # Send timestamp and distance data back to the main thread for plotting
        queue.put(snolog.unix_time)
        queue.put(snolog.lidar_tc_distance)

        t_end = time()

        # Compute the elapsed time between triggering the measurement and being ready to
        # wait for the next measurement. This ensures the measurement interval timing is more
        # precise.
        elapsed_time = t_end - t_start

        # We can't have a measurement interval that is less than the elapsed time for a
        # measurement, so we need to ensure the measurement_interval is greater than
        # the elapsed time; if it's not, we can sleep.
        sleep_time = measurement_interval - read_delay - elapsed_time
        if sleep_time > 0:
            sleep(sleep_time)
        else:
            pass

    serial_port.close()


def main(
    serial_port, csv_filename, measurement_interval=30, read_delay=0, verbose=False
):
    """Main entry point for the application.

    This sets up signal handling, starts the lidar control thread, and initializes
    the real-time plotting interface.

    Args:
        serial_port: The serial port device (e.g., "/dev/ttyUSB0", "COM1").
        csv_filename: Path to the output CSV file.
        measurement_interval: Seconds between measurements.
        read_delay: Delay before reading after triggering a measurement.
        verbose: Boolean for verbose printing. If True, the snolog packets are printed.
    """
    global interrupted

    signal.signal(signal.SIGINT, sigint_handler)

    # We're sending two data points at a time back to the main thread, so
    # we limit the queue size to 2. This lets us check if the lidar control thread
    # is finished sending data by checking if the queue is full.
    queue = Queue(maxsize=2)

    lidar_control_thread = threading.Thread(
        target=lidar_control,
        args=(
            serial_port,
            csv_filename,
            measurement_interval,
            read_delay,
            verbose,
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
    plt.title(csv_filename)

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

    plt.show(block=False)

    while not interrupted:
        plt.pause(5)

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
            - verbose: Boolean for verbose printing
    """
    parser = argparse.ArgumentParser(
        description="Manually trigger lidar measurements at a specified interval, then log and plot snolog data. This program is designed for SNOdars that are configured in 'manual' mode.",
        allow_abbrev=False,
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

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print out snolog and health flags for each measurement.",
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
        verbose=args.verbose,
    )
