#!/usr/bin/env python3
"""Veille radio : attend la RC-N1, lance dji_host.py, recommence si on la débranche.

Utilisé par scripts/start.sh et scripts/start.bat. Ctrl+C arrête la veille,
pas le simulateur (scripts/stop.sh / stop.bat pour ça).
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from dji_host import DJI_VID, get_dji_vid  # noqa: E402
import serial.tools.list_ports  # noqa: E402

HOST_PY = os.path.join(HERE, "dji_host.py")
CALIB = os.path.join(HERE, "rc_calib.json")
POLL_S = 2.0
REMINDER_S = 15.0


def rc_present():
    for port in serial.tools.list_ports.comports(True):
        desc = port.description or ""
        if "DJI USB VCOM" in desc or "DEVICE USB VCOM" in desc:
            return True
        if get_dji_vid(port) == DJI_VID:
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
    waiting_msg_shown = False
    try:
        while True:
            if not rc_present():
                now = time.time()
                if not waiting_msg_shown or (now - last_reminder) >= REMINDER_S:
                    print("  En attente de la RC-N1...", flush=True)
                    waiting_msg_shown = True
                    last_reminder = now
                time.sleep(POLL_S)
                continue

            waiting_msg_shown = False
            cmd = [sys.executable, HOST_PY]
            if not os.path.isfile(CALIB):
                print("RC détectée — première fois : calibration, puis pilotage.")
                cmd.append("--calibrate")
            else:
                print("RC détectée — lecture des sticks.")

            # 0 = arrêt propre (Ctrl+C dans dji_host). Autre = débranchée / erreur.
            rc = subprocess.call(cmd)
            if rc == 0:
                print("Lecture arrêtée. En attente d'une RC...")
            else:
                print("RC débranchée ou lecture interrompue. Nouvel essai dès qu'elle revient...")
            last_reminder = 0.0
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nVeille radio arrêtée. Le simulateur tourne encore.")
        print("  Arrêt complet : scripts/stop.sh  (ou stop.bat)")
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
