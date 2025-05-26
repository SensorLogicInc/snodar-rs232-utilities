import serial
import argparse
import matplotlib
import matplotlib.animation as animation
from datetime import datetime
from matplotlib import pyplot as plt
from queue import Queue
import threading
import csv
import signal
import sys
import os
from time import sleep

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

NUS_USA = "!USA\r".encode("utf-8")
NUS_DISABLE_TIMER = "!PT0\r".encode("utf-8")

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


def trigger_lidar_conversion(serial_port):
    nbytes = serial_port.write(NUS_USA)
    if nbytes != 5:
        print("something went wrong...?")


def read_snolog(serial_port):
    snolog = serial_port.read(128)

    return snolog


def main(measurement_interval, read_delay):
    global interrupted

    signal.signal(signal.SIGINT, sigint_handler)

    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    while True:
        trigger_lidar_conversion(serial_port)
        sleep(read_delay)
        snolog = read_snolog(serial_port)
        print(snolog)
        sleep(measurement_interval - read_delay)


def parse_args():

    parser = argparse.ArgumentParser(
        prog="SNOdar RS232 snolog data logger",
        description="Log and plot snolog data over RS232",
    )

    parser.add_argument(
        "--measurement-interval", default=30, help="How often to take measurements"
    )
    parser.add_argument(
        "--read-delay",
        default=15,
        help="How long to wait before reading snolog data after triggering a measurement",
    )

    args = parser.parse_args()

    return args


if __name__ == "__main__":

    args = parse_args()

    main(measurement_interval=args.measurement_interval, read_delay=args.read_delay)
