#!/usr/bin/env python3
"""Veille radio : attend que la RC-N1 réponde au protocole, puis lance dji_host.

Ctrl+C arrête la veille, pas le simulateur (scripts/stop.sh / stop.bat).
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from dji_host import find_port  # noqa: E402

HOST_PY = os.path.join(HERE, "dji_host.py")
CALIB = os.path.join(HERE, "rc_calib.json")
POLL_S = 2.0
RETRY_S = 4.0
REMINDER_S = 15.0


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
            # On ne lance dji_host QUE si le port protocole répond vraiment
            # (pas juste « un USB DJI est branché » : il y a aussi un port Log).
            dev = find_port(verbose=False)
            if not dev:
                now = time.time()
                if not waiting or (now - last_reminder) >= REMINDER_S:
                    print("  En attente de la RC-N1...", flush=True)
                    waiting = True
                    last_reminder = now
                time.sleep(POLL_S)
                continue

            waiting = False
            cmd = [sys.executable, HOST_PY, dev]
            if not os.path.isfile(CALIB):
                print(f"RC prête sur {dev} — première fois : calibration, puis pilotage.")
                cmd.append("--calibrate")
            else:
                print(f"RC prête sur {dev} — lecture des sticks.")

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
