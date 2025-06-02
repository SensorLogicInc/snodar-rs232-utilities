import argparse
import threading
import signal
import sys
import os
import serial
import matplotlib
import matplotlib.animation as animation
from datetime import datetime
from matplotlib import pyplot as plt
from queue import Queue
from time import sleep

from snolog_parser import create_snolog_csv, append_snolog_to_csv


NUS_USA = "!USA\r".encode("utf-8")

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

def trigger_lidar_conversion(serial_port):
    nbytes = serial_port.write(NUS_USA)
    if nbytes != 5:
        print("something went wrong...?")


def read_snolog(serial_port):
    snolog = serial_port.read(128)

    return snolog


def lidar_control(serial_port, csv_filename, measurement_interval, read_delay, queue):
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
        queue.put(snolog.seasonal_snow_depth)

        sleep(measurement_interval - read_delay)

    serial_port.close()


def main(serial_port, csv_filename, measurement_interval=30, read_delay=15):
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
    plt.ylabel("Depth (m)")

    # Add padding so the x-axis label doesn't get cut off due to the rotated
    # tick labels.
    plt.subplots_adjust(bottom=0.18)

    xdata = []
    ydata = []

    def fetch_data():
        if queue.full():
            timestamp = queue.get()
            snow_depth = queue.get()

            yield timestamp, snow_depth
        else:
            yield None

    def update_plot(frame):
        if frame:
            timestamp = datetime.fromtimestamp(frame[0])
            snow_dpeth = frame[1]

            xdata.append(timestamp)
            ydata.append(snow_dpeth)

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
    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 snolog data logger",
        description="Log and plot snolog data over RS232",
    )

    parser.add_argument(
        "serial_port", help="Serial port number, e.g., /dev/ttyUSB0, COM7"
    )
    parser.add_argument("csv", help="Output CSV file name")
    parser.add_argument(
        "--measurement-interval",
        type=int,
        default=30,
        help="How often to take measurements",
    )
    parser.add_argument(
        "--read-delay",
        type=int,
        default=15,
        help="How long to wait before reading snolog data after triggering a measurement",
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
