# SNOdar RS232 utilities

This repository contains various utilities for triggering measurements and logging data via RS232:

- `manual_data_capture.py`: Manually trigger measurements; plot measurement data and save to a csv.
- `snolog_parser.py`: Utility functions for parsing and saving raw snolog data.
- `ascii_data_logger.py`: For sensors that are configured in "snow depth" mode (i.e., measurements aren't triggered manually) and logs data over RS232 in ASCII format, this script will save and plot the logged data.

## Installation

### Getting the code

You can either
- clone this repository using git: `git clone https://github.com/SensorLogicInc/snodar-rs232-utilities.git`
- [download a zip file](https://github.com/SensorLogicInc/snodar-rs232-utilities/archive/refs/heads/main.zip)

### Installing dependencies

Make sure you have python installed. On Linux and macOS, the system will already have some version of python. For Windows, use the [python install manager](https://www.python.org/downloads/release/pymanager-250b9/), [miniforge](https://github.com/conda-forge/miniforge), or [Anaconda Navigator](https://www.anaconda.com/download/success).

These utilities require pyserial for serial communication and matplotlib for plotting. The dependencies can be installed via one of the methods listed below.

> [!TIP]
> All the commands below assume you're in the `snodar-rs232-utilities` directory.

#### pip and venv

1. If `pip` isn't installed, [install pip](https://pip.pypa.io/en/stable/installation/):
   ```
   python -m ensurepip --upgrade
   ```
2. Create a virtual environment to install the dependencies into:
   ```
   python -m venv ./venv/snodar-rs232-utilities
   ```
3. [Activate the virtual environment](https://docs.python.org/3/library/venv.html#how-venvs-work)

- Linux/macOS: `source ./venv/snodar-rs232-utilities/bin/activate`
- Windows:
  - CMD: `source .\venv\snodar-rs232-utilities\Scripts\activate.bat`
  - Powershell: `source .\venv\snodar-rs232-utilities\Scripts\activate.ps1`

4. Install the dependencies:
   ```
   pip install .
   ```
   
> [!IMPORTANT]
> You must be in the `snodar-rs232-utilities` directory when running `pip install .`

#### uv

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Install depedendencies:
   ```
   uv sync
   ```

#### mamba/conda

If you installed mamba or conda through miniforge or Anaconda, you can create an environment and install the dependencies as follows:

```
mamba env create -f env.yaml
```

## Running the scripts

### pip and venv

1. Make sure the environment is activated:
   ```
   source ./venv/snodar-rs232-utilities
   ```
2. Run a script with python: `python <script-name>.py`

### uv

Run the program with `uv run`. For example:

```
uv run rs232_data_capture.py COM4 output.csv
```

### mamba/conda

1. Activate the environment:
   ```
   mamba activate snodar-rs232-utilities
   ```
2. Run the script using `python <script-name>.py`

## `manual_data_capture.py`

`manual_data_capture.py` is used for manually triggering measurements via RS-232 and recording and plotting the snolog data that gets returned. Essentially, the program continually sends the `!USA` command to a SNOdar at a given internal, parses the resulting snolog, and then plots the distance.

> [!IMPORTANT]
> This program expects the SNOdar to be configured in "manual" mode. "Manual" mode disables the SNOdar's measurement timer; disabling the measurement timer ensures that automated measurements don't interfere with our manual measurements.

The parsed snolog data will be printed in the terminal in addition to being saved in a CSV.

### Usage

```
usage: manual_data_capture.py [-h] [--measurement-interval MEASUREMENT_INTERVAL] [--read-delay READ_DELAY]
                              serial_port csv

Manually trigger lidar measurements at a specified interval, then log and plot snolog data. This program is designed
for SNOdars that are configured in 'manual' mode.

positional arguments:
  serial_port           Serial port number, e.g., /dev/ttyUSB0, COM7
  csv                   Output CSV file name

options:
  -h, --help            show this help message and exit
  --measurement-interval MEASUREMENT_INTERVAL
                        How often to take measurements. Default = 30 seconds
  --read-delay READ_DELAY
                        How long to wait before reading snolog data after triggering a measurement. Default = 0 seconds
```

> [!NOTE]
> The `--read-delay` parameter is  not strictly necessary. Reading from the serial port is set up as a non-blocking operation, so there doesn't need to be a delay to wait for the data to be ready. This is why the default value is 0.

> [!TIP]
> To exit the program, press ctrl+c in the terminal.

#### Examples

**15-second measurement interval**:
```bash
python manual_data_capture.py --measurement-interval 15 COM3 output.csv
```

**30-second measurement interval with a 15-second delay before reading from the serial port**:
```bash
python manual_data_capture.py --measurement-interval 30 --read-delay 15 /dev/ttyUSB0 output.csv
```


## `ascii_data_logger.py`

`ascii_data_logger.py` is used for logging ASCII data. This assumes the sensor is configured in "snow depth" mode, the periodic measurement timer is active, and RS-232 TX is configured for ASCII mode.

The ASCII data will be printed in the terminal in addition to being saved in a CSV.

### Usage

```
usage: ascii_data_logger.py [-h] serial_port csv

Log and plot ASCII data over RS232

positional arguments:
  serial_port  Serial port number, e.g., /dev/ttyUSB0, COM7
  csv          CSV filename to log data to

options:
  -h, --help   show this help message and exit
```

#### Examples
**Windows serial port**:
```bash
python snolog_parser.py COM4 output.csv
```

**Linux serial port**:
```bash
python snolog_parser.py /dev/ttyUSB0 output.csv
```

## `snolog_parser.py`

`snolog_parser.py` mainly contains utility functions for parsing raw snolog data. These functions are used in `manual_data_capture.py`. However, `snolog_parser.py` has a CLI program that can convert raw snolog data into a CSV. The raw data must be in binary format.

### Usage

```
usage: snolog_parser.py [-h] hex_file csv_file

Convert raw snologs in hex into a csv file

positional arguments:
  hex_file    input hex file log
  csv_file    output csv file

options:
  -h, --help  show this help message and exit
```

#### Example
```bash
python snolog_parser.py raw_data.bin parsed_data.csv
```
