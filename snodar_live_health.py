"""Utilities for parsing and validating health flags from a SNOdar device.

This module defines a `SnodarLiveHealthFlags` named tuple that holds these status flags,
and provides functions to parse raw health bytes into this structure and validate its contents.
"""

import warnings
from collections import namedtuple

SnodarLiveHealthFlags = namedtuple(
    "SnodarLiveHealthFlags",
    [
        "lidar_count_ok",
        "lidar_time_ok",
        "lidar_registers_ok",
        "rtc_read_ok",
        "rtc_time_increased",
        "ina_voltage_ok",
        "ina_current_ok",
        "nrf_temperature_ok",
        "tmp1075_temperature_ok",
        "lidar_pcb_temperature_ok",
        "lidar_soc_temperature_ok",
        "imu_ready",
        "imu_quaternion_ok",
    ],
)
"""NamedTuple for SNOdar live health flags.

Attributes:
    lidar_count_ok: Was the lidar measurement count correct?
    lidar_time_ok: True is the lidar didn't timeout, False if it did timeout.
    lidar_registers_ok: Were the lidar registers okay?
    rtc_read_ok: Was the SNOdar able to read from the RTC?
    rtc_time_increased: Did the RTC's time increase from the last time?
    ina_voltage_ok: Was the INA voltage reading okay?
    ina_current_ok: Was the INA current reading okay?
    nrf_temperature_ok: nRF temperature reading status
    tmp1075_temperature_ok: TMP1075 temperature reading status
    lidar_pcb_temperature_ok: Lidar PCB temperature reading status
    lidar_soc_temperature_ok: Lidar SoC temperature reading status
    imu_ready: Was the IMU data ready?
    imu_quaternion_ok: Was the IMU quaternion data valid?
"""


def parse_flags(health_flags_high, health_flags_low):
    """Parse the raw health flag bytes into a SnodarLiveHealthFlags tuple.

    Args:
        health_flags_high: The health flags high byte in the snolog packet.
        health_flags_low: The health flags low byte in the snolog packet.

    Returns:
        live_health: SnodarLiveHealthFlags tuple with the parsed flag values.
    """
    # Low-byte flag bitmasks
    IMU_READY = 1 << 0
    INA_V_ROK = 1 << 1
    INA_A_ROK = 1 << 2
    NRF_ROK = 1 << 3
    TMP_ROK = 1 << 4
    LDR_PCB_ROK = 1 << 5
    LDR_SOC_ROK = 1 << 6
    IMU_DOK = 1 << 7

    # High-byte flag bitmasks
    RTC_ROK = 1 << 0
    RTC_TOK = 1 << 1
    LIDAR_CNT_OK = 1 << 2
    LIDAR_TOK = 1 << 3
    LIDAR_REG_OK = 1 << 4

    live_health = SnodarLiveHealthFlags(
        lidar_count_ok=True if health_flags_high & LIDAR_CNT_OK else False,
        lidar_time_ok=True if health_flags_high & LIDAR_TOK else False,
        lidar_registers_ok=True if health_flags_high & LIDAR_REG_OK else False,
        rtc_read_ok=True if health_flags_high & RTC_ROK else False,
        rtc_time_increased=True if health_flags_high & RTC_TOK else False,
        ina_voltage_ok=True if health_flags_low & INA_V_ROK else False,
        ina_current_ok=True if health_flags_low & INA_A_ROK else False,
        nrf_temperature_ok=True if health_flags_low & NRF_ROK else False,
        tmp1075_temperature_ok=True if health_flags_low & TMP_ROK else False,
        lidar_pcb_temperature_ok=True if health_flags_low & LDR_PCB_ROK else False,
        lidar_soc_temperature_ok=True if health_flags_low & LDR_SOC_ROK else False,
        imu_ready=True if health_flags_low & IMU_READY else False,
        imu_quaternion_ok=True if health_flags_low & IMU_DOK else False,
    )

    return live_health


def check_flags(live_health):
    """Issue warnings if any health flags are False.

    A false health flag indicates that something went wrong with that sensor.

    Args:
        live_health: SnodarLiveHealthFlags tuple.
    """
    if not live_health.lidar_count_ok:
        warnings.warn("lidar measurement count was not ok")
    if not live_health.lidar_time_ok:
        warnings.warn("lidar timeout occurred!")
    if not live_health.lidar_registers_ok:
        warnings.warn("lidar registers were not ok")
    if not live_health.rtc_read_ok:
        warnings.warn("RTC read was not ok")
    if not live_health.rtc_time_increased:
        warnings.warn("RTC time didn't increase")
    if not live_health.ina_voltage_ok:
        warnings.warn("INA voltage read was not ok")
    if not live_health.ina_current_ok:
        warnings.warn("INA current read was not ok")
    if not live_health.nrf_temperature_ok:
        warnings.warn("nRF temperature read was not ok")
    if not live_health.tmp1075_temperature_ok:
        warnings.warn("TMP1075 temperature read was not ok")
    if not live_health.lidar_pcb_temperature_ok:
        warnings.warn("lidar pcb temperature read was not ok")
    if not live_health.lidar_soc_temperature_ok:
        warnings.warn("lidar SoC temperature read was not ok")
    if not live_health.imu_ready:
        warnings.warn("IMU data was not ready")
    if not live_health.imu_quaternion_ok:
        warnings.warn("IMU quaternion was not ok")
