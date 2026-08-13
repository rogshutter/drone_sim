#!/usr/bin/env python3
"""Veille radio : dès qu'un USB DJI est là, lance dji_host (lui seul ouvre le port)."""

import os
import subprocess
import sys
import time

import serial.tools.list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from dji_host import DJI_VID, get_dji_vid, is_log_interface, is_protocol_interface  # noqa: E402

HOST_PY = os.path.join(HERE, "dji_host.py")
CALIB = os.path.join(HERE, "rc_calib.json")
POLL_S = 2.0
RETRY_S = 5.0
REMINDER_S = 15.0


def rc_plugged():
    """True si un USB DJI (hors canal Log) est listé — sans ouvrir le port."""
    for port in serial.tools.list_ports.comports(True):
        if is_log_interface(port):
            continue
        if is_protocol_interface(port) or get_dji_vid(port) == DJI_VID:
            return True
    return False


def main():
    print()
    print("Veille radio RC-N1")
    print("  Branche la radio (USB-C du dessous) et allume-la quand tu veux.")
    print("  Ctrl+C : arrête la veille — le simulateur continue.")
    print("  Pour tout éteindre : scripts/stop.sh  (ou stop.bat)")
    print()

    last_reminder = 0.0
    waiting = False
    try:
        while True:
            if not rc_plugged():
                now = time.time()
                if not waiting or (now - last_reminder) >= REMINDER_S:
                    print("  En attente de la RC-N1...", flush=True)
                    waiting = True
                    last_reminder = now
                time.sleep(POLL_S)
                continue

            waiting = False
            time.sleep(1.5)  # laisser l'USB finir de s'annoncer
            cmd = [sys.executable, HOST_PY]
            if not os.path.isfile(CALIB):
                print("RC branchée — première fois : calibration, puis pilotage.")
                cmd.append("--calibrate")
            else:
                print("RC branchée — lecture des sticks.")

            rc = subprocess.call(cmd)
            if rc == 0:
                print("Lecture arrêtée. En attente d'une RC...")
            else:
                print("Lecture interrompue. Nouvel essai dans quelques secondes...")
            last_reminder = 0.0
            time.sleep(RETRY_S)
    except KeyboardInterrupt:
        print("\nVeille radio arrêtée. Le simulateur tourne encore.")
        print("  Arrêt complet : scripts/stop.sh  (ou stop.bat)")
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
