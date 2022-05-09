#!/usr/bin/env python3

import argparse
import json
import os

def nbt_prettyjson():
    parser = argparse.ArgumentParser(description="nt_prettyjson.py pretty prints your json file .")
    parser.add_argument("json_in", help="input json file", type=str)
    parser.add_argument("json_out", help="output json file ", type=str)
    args = parser.parse_args()
 
    with open(args.json_in, "r") as f:
        data = json.load(f)

    with open(args.json_out, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)

    os.chmod(args.json_out, 0o775)

if __name__ == "__main__":
    nbt_prettyjson()
