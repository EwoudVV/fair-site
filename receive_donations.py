#!/usr/bin/env python3
"""Pull donation records from the Nest box backend to this laptop.

Run on this machine:
    python3 receive_donations.py

Requires SSH access to the Nest box (edit NEST_HOST below, or pass --host).
Fetches /opt/fair/data/donations.jsonl, appends to a local archive,
and clears the file on the Nest box.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

LOCAL_DIR = Path.home() / "fair-donations"
LOCAL_DIR.mkdir(exist_ok=True)
LOCAL_ARCHIVE = LOCAL_DIR / "donations.jsonl"

NEST_HOST = "duck@hackclub.app"  # stable Hack Club nest relay
NEST_PATH = "/opt/fair/data/donations.jsonl"


def ssh_run(host, args, check=True):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def main():
    global NEST_HOST
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=NEST_HOST, help="ssh host for the Nest box")
    args = ap.parse_args()
    if not args.host:
        print("Set NEST_HOST in this script or pass --host <user@host>")
        sys.exit(1)

    print(f"Fetching donations from {args.host} ...")
    r = ssh_run(args.host, ["cat", NEST_PATH], check=False)
    if r.returncode != 0:
        print("No access or file missing on Nest box (that's fine if empty).")
        if r.stderr.strip():
            print("  " + r.stderr.strip().splitlines()[-1])
        return
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if not lines:
        print("No donations on the Nest box yet.")
        return

    with open(LOCAL_ARCHIVE, "a", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")

    ssh_run(args.host, ["sh", "-c", f": > {NEST_PATH}"])
    print(f"Saved {len(lines)} donation(s) to {LOCAL_ARCHIVE}")
    print("Nest box file cleared.")


if __name__ == "__main__":
    main()