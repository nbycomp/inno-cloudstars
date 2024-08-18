#!/usr/bin/env python3

import os
import glob

# https://stackoverflow.com/a/73195814
def read_last_line(filename):
    """Returns the last full line in the file. A full line is a line that ends with a newline character"""
    num_newlines = 0
    with open(filename, 'rb') as f:
        first_line = f.readline().decode()
        try:
            f.seek(-1, os.SEEK_END)
            while True:
                if f.read(1) == b'\n':
                    num_newlines += 1
                if num_newlines >= 2:
                    break
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last_line = f.readline().decode()
    return (first_line, last_line)

if __name__ == "__main__":
    stat_files = glob.glob("/opencraft2/logs/*.csv")
    for filename in stat_files:
        measurement_name = filename.split("/")[-1].split(".")[0]
        first_line, last_line = read_last_line(filename)
        headers = first_line.strip().lower().replace(" ", "_").split(";")
        data = last_line.strip().split(";")
        output = measurement_name
        for i in range(len(headers)):
            output += f" {headers[i]}={data[i]}i"
        print(output)
