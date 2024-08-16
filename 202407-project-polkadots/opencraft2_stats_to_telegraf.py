#!/usr/bin/env python3

import os

# https://stackoverflow.com/a/73195814
def read_n_to_last_line(filename, n = 1):
    """Returns the nth before last line of a file (n=1 gives last line)"""
    num_newlines = 0
    with open(filename, 'rb') as f:
        first_line = f.readline().decode()
        try:
            f.seek(-2, os.SEEK_END)
            while num_newlines < n:
                f.seek(-2, os.SEEK_CUR)
                if f.read(1) == b'\n':
                    num_newlines += 1
        except OSError:
            f.seek(0)
        last_line = f.readline().decode()
    return (first_line, last_line)

if __name__ == "__main__":
    filename = "/opencraft2/logs/opencraft2_client_stats.csv"
    first_line, last_line = read_n_to_last_line(filename, n = 2)
    headers = first_line.strip().lower().replace(" ", "_").split(";")
    data = last_line.strip().split(";")
    output = "opencraft2_stats"
    for i in range(len(headers)):
        output += f" {headers[i]}={data[i]}i"
    print(output)
