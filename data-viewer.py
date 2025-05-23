import serial
import pandas as pd

if __name__ == "__main__":

    df = pd.DataFrame(
        columns=[
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
            "Seasonsal Snow Depth",
            "Seasonal Snow Fall",
            "New Snow Fall",
            "DoY SWE",
            "Temp SWE",
        ],
    )

    serial_port = serial.Serial(port="/dev/ttyUSB0", baudrate=19200)

    print(df.columns)

    while True:
        raw_bytes = serial_port.readline()

        csv_string = raw_bytes.decode()

        csv_list = csv_string.strip().split(",")

        data = [float(x) for x in csv_list]

        df.loc[len(df)] = data

        # print(df)
        print(data)

    serial_port.close()
