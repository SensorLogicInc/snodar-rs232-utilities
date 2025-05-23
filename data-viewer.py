import serial
import pandas as pd
from queue import Queue
import threading

def read_rs232_data(queue):
    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    while True:
        raw_bytes = serial_port.readline()

        csv_string = raw_bytes.decode()

        csv_list = csv_string.strip().split(",")

        data = [float(x) for x in csv_list]

        queue.put(data)

    # TODO: graceful exit
    serial_port.close()


if __name__ == "__main__":

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

    while True:
        if not queue.empty():
            print(queue.get())

