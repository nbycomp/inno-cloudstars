#!/usr/bin/env python3

import os

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
    filename = "/opencraft2/logs/opencraft2_client_stats.csv"
    first_line, last_line = read_last_line(filename)
    headers = first_line.strip().lower().replace(" ", "_").split(";")
    data = last_line.strip().split(";")
    output = "opencraft2_stats"
    for i in range(len(headers)):
        output += f" {headers[i]}={data[i]}i"
    print(output)
