import csv
import struct
from typing import NamedTuple


class Snolog(NamedTuple):
    """NamedTuple for snolog logs"""

    id: int  # uint8, 1 byte
    version: int  # uint8, 1 byte
    length: int  # uint16, 2 bytes
    unix_time: int  # uint32, 4 bytes
    power_mA: int  # int16, 2 bytes
    power_V: int  # int16, 2 bytes
    pcb_temperature: float  # 4 bytes, deg C
    imu_temperature: float  # 4 bytes, deg C
    imu_quaternian0: float  # 4 bytes, versors
    imu_quaternian1: float  # 4 bytes, versors
    imu_quaternian2: float  # 4 bytes, versors
    imu_quaternian3: float  # 4 bytes, versors
    imu_roll: float  # 4 bytes, radians
    imu_pitch: float  # 4 bytes, radians
    imu_yaw: float  # 4 bytes, radians
    imu_flag: int  # uint8, 1 byte
    heater_enable: int  # uint8, 1 byte
    lidar_soc_temperature: int  # int8, 1 byte, deg C
    lidar_pcb_temperature: int  # int8, 1 bytes, deg C
    lidar_raw_distance: float  # 4 bytes, meters
    lidar_doff_distance: float  # 4 bytes, meters
    lidat_tc_distance: float  # 4 bytes, meters
    lidar_meas_time: int  # uint16, 2 bytes, seconds
    lidar_status: int  # uint8, 1 byte
    nrf_temperature: int  # int8, 1 byte, deg C
    outside_temperature: float  # 4 bytes, deg C
    seasonal_snow_depth: float  # 4 bytes, meters
    seasonsal_snow_fall: float  # 4 bytes, meters
    new_snow_fall: float  # 4 bytes, meters
    doy_swe: float  # 4 bytes, meters
    temp_swe: float  # 4 bytes, meters
    sc_daily_max_time: int  # int32, 4 bytes
    sc_daily_max_depth: float  # 4 bytes
    sc_daily_min_time: int  # int32, 4 bytes
    sc_daily_min_depth: float  # 4 bytes
    sc_abs_min_time: int  # int32, 4 bytes
    sc_abs_min_depth: float  # 4 bytes
    sc_min_max_cntr: int  # int32, 4 bytes
    sc_daily_acc_sf: float  # 4 bytes
    health_flags_lo: int  # uint8, 1 byte
    health_flag_hi: int  # uint8, 1 byte
    reserved: int  # 1 byte
    checksum: int # uint8, 1 byte


def parse_raw_snolog(raw_bytes):
    unpacked = struct.unpack("=BBHLhhfffffffffBBbbfffHBbfffffflflflflfBBBB", raw_bytes)

    snolog = Snolog(*unpacked)
    return snolog


def create_snolog_csv(filename):
    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file, dialect="excel")
        writer.writerow(Snolog._fields)


def append_snolog_to_csv(filename, snolog):
    with open(filename, 'a') as csv_file:
        writer = csv.writer(csv_file, dialect="excel")
        writer.writerow(snolog)