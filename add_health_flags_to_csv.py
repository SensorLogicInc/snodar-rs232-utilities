"""Parse live health flag bytes from a csv into their individual flags.

This script adds the parsed flags to the original csv, overwriting the original file.
"""
import argparse
import csv

import snodar_live_health


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("csv", help="The CSV file to expand flag statuses in. *This CSV will be modified*.")

    args = parser.parse_args()

    return args

def main(filename):
    with open(filename, 'r+') as csv_file:
        reader = csv.DictReader(csv_file, dialect="excel")
        rows = list(reader)

        for row in rows:
            if "health_flags_hi" in row.keys():
                # This is a log captured via rs-232.
                health_flags = snodar_live_health.parse_flags(int(row["health_flags_hi"]), int(row["health_flags_lo"]))

            elif "LIVE_HEALTH_FLAGS" in row.keys():
                # This is a log downloaded from mobile app, so we have to split the flags into
                # low and high bytes
                high_byte = (int(row["LIVE_HEALTH_FLAGS"], 16) & 0xff00) >> 8
                low_byte = int(row["LIVE_HEALTH_FLAGS"], 16) & 0xff

                health_flags = snodar_live_health.parse_flags(high_byte, low_byte)
            else:
                raise RuntimeError("CSV file doesn't have health flags in it.")

            # Add the parsed health flags to the csv row
            for i, flag in enumerate(health_flags._fields):
                row[flag] = health_flags[i]

        # Move back to the beginning of the file
        csv_file.seek(0)

        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

if __name__ == "__main__":
    args = parse_args()

    main(args.csv)
