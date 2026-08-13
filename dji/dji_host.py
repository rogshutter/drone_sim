#!/usr/bin/env python3
"""
dji_host.py — Lecture de la télécommande DJI RC-N1 (sans écran) et envoi UDP.

Cross-platform (Windows et Linux) : aucune dépendance spécifique à un OS.
Remplace vgamepad par un envoi réseau UDP : le stick / la molette partent vers
un conteneur ROS2 (service `ros`, port UDP 7777) qui publie sensor_msgs/Joy.

Utilisation :
    python dji_host.py                       # détection auto du port + envoi 127.0.0.1:7777
    python dji_host.py COM7                  # forcer le port série
    python dji_host.py --target 192.168.1.50 # changer la destination UDP
    python dji_host.py --live                # afficher les valeurs sans envoyer
    python dji_host.py --calibrate           # calibrer la RC (centre + butées) puis piloter

Calibration : mesure le centre réel et les butées de chaque axe, avec une zone
morte au centre (option --deadzone). Résultat sauvé dans dji/rc_calib.json et
réappliqué automatiquement aux lancements suivants.

Dépendance : pyserial (`pip install -r requirements.txt`).
"""

import argparse
import json
import os
import socket
import struct
import sys
import time

import serial
import serial.tools.list_ports

DJI_REQUEST = bytearray.fromhex('55 0d 04 33 0a 06 eb 34 40 06 01 74 24')
# Active le mode simulateur RC (sinon les sticks arrivent trop lentement
# et l'USB se coupe). Même paquet que DjiMini2RCasJoystick.
DJI_SIM_MODE = bytearray.fromhex('55 0e 04 66 0a 06 eb 34 40 06 24 01 d9 ec')
DJI_VID = 0x2CA3
BAUD = 115200

# Axes (offsets reverse-engineered dans dji.py, communs à Windows et Linux)
FIELDS = {'rx': (13, 15), 'ry': (16, 18), 'ly': (19, 21), 'lx': (22, 24), 'cam': (25, 27)}
AXES = ['lx', 'ly', 'rx', 'ry', 'cam']

MAX_OUT = 32767   # plage de sortie envoyée en UDP : ±32767 (centre 0)

# Fichier de calibration, à côté du script (dji/rc_calib.json).
CALIB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rc_calib.json')


def parse_input(byte):
    """Convertit une valeur DJI (centre 1024, min 364, max 1684) en plage ±32767."""
    raw = int.from_bytes(byte, byteorder='little')
    return int((raw - 1024) * 65535 / (1684 - 364))


# ---------------------------------------------------------------------------
# Calibration RC : centre réel + butées réelles + zone morte, par axe.
# La calibration s'applique sur les valeurs déjà mises à l'échelle (±32767).
# But : centre parfaitement neutre (pas de dérive) et pleine amplitude propre.
# ---------------------------------------------------------------------------
def load_calib(path=CALIB_PATH):
    """Charge la calibration si le fichier existe, sinon None."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_calib(calib, path=CALIB_PATH):
    with open(path, 'w') as f:
        json.dump(calib, f, indent=2)


def norm_axis(v, cal, deadzone):
    """Ramène v (±32767 brut) en ±32767 calibré : centre -> 0, butée -> ±32767,
    avec une zone morte (fraction de la course, ex. 0.03) autour du centre."""
    c = cal.get('center', 0)
    lo = cal.get('min', -MAX_OUT)
    hi = cal.get('max', MAX_OUT)
    span = max(hi - c, 1) if v >= c else max(c - lo, 1)
    out = (v - c) / span                       # -1 .. +1
    if abs(out) < deadzone:
        return 0
    sign = 1.0 if out > 0 else -1.0
    out = sign * (abs(out) - deadzone) / (1.0 - deadzone)   # remise à l'échelle
    return int(max(-1.0, min(1.0, out)) * MAX_OUT)


def apply_calib(state, calib, deadzone):
    """Applique la calibration à tout l'état {lx,ly,rx,ry,cam}."""
    if not calib:
        # Pas de calibration : centre 0, ±32767, mais on garde la zone morte.
        return {k: norm_axis(v, {}, deadzone) for k, v in state.items()}
    return {k: norm_axis(v, calib.get(k, {}), deadzone) for k, v in state.items()}


def _collect(ser, seconds):
    """Lit des états pendant `seconds` et renvoie la liste des dicts lus."""
    out = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        out.append(read_state(ser))
    return out


def run_calibration(ser, path=CALIB_PATH):
    """Calibration interactive : mesure le centre puis les butées de chaque axe."""
    print('\n=== Calibration de la RC ===')
    print('Étape 1/2 : LÂCHE tous les sticks (position centre) et NE TOUCHE PAS.')
    input('  Appuie sur Entrée quand les sticks sont au centre... ')
    print('  Mesure du centre (2 s)...')
    center_samples = _collect(ser, 2.0)
    center = {a: int(sorted(s[a] for s in center_samples)[len(center_samples) // 2])
              for a in AXES}   # médiane = robuste au bruit

    print('\nÉtape 2/2 : BOUGE tous les sticks ET la molette dans TOUTES les')
    print('directions, jusqu\'aux butées, pendant 6 s.')
    input('  Appuie sur Entrée puis bouge tout... ')
    print('  Enregistrement des butées (6 s)... BOUGE !')
    ext = _collect(ser, 6.0)
    calib = {}
    for a in AXES:
        vals = [s[a] for s in ext] + [center[a]]
        calib[a] = {'min': int(min(vals)), 'center': center[a], 'max': int(max(vals))}

    save_calib(calib, path)
    print(f'\nCalibration enregistrée dans {path} :')
    for a in AXES:
        c = calib[a]
        print(f"  {a:3s}: min={c['min']:+6d}  centre={c['center']:+6d}  max={c['max']:+6d}")
    print('=== Calibration terminée ===\n')
    return calib


def get_dji_vid(port):
    try:
        if 'VID:PID=' in port.hwid:
            vid = port.hwid.split('VID:PID=')[1].split()[0].split(':')[0]
            return int(vid, 16)
    except Exception:
        pass
    return None


def _desc(port):
    return (port.description or "").lower()


def is_log_interface(port):
    """Le canal 'Log ACM' de la RC-N1 / C5 n'émet pas les sticks — on ne le sonde pas."""
    return "log" in _desc(port)


def is_protocol_interface(port):
    d = _desc(port)
    return any(s in d for s in (
        "vcom for protocol", "device usb vcom", "v1 acm", "protocol",
    ))


def open_rc_serial(port_name):
    """Ouvre le port comme DjiMini2RCasJoystick (115200 + mode simulateur)."""
    ser = serial.Serial(
        port=port_name,
        baudrate=BAUD,
        timeout=1.0,
        write_timeout=1.0,
        dsrdtr=False,
        rtscts=False,
    )
    time.sleep(0.3)
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    ser.write(DJI_SIM_MODE)
    ser.flush()
    time.sleep(0.15)
    return ser


def find_open_serial(forced=None, verbose=True):
    """Ouvre le port C5 / protocole. Pas de test write/read : ça reset l'USB."""
    if forced:
        try:
            return open_rc_serial(forced)
        except Exception as e:
            if verbose:
                print(f'Impossible d\'ouvrir {forced} : {e}')
            return None

    protocol, other = [], []
    seen = set()
    for port in serial.tools.list_ports.comports(True):
        if port.device in seen:
            continue
        seen.add(port.device)
        if is_log_interface(port):
            continue
        if is_protocol_interface(port):
            protocol.append(port)
        elif get_dji_vid(port) == DJI_VID:
            other.append(port)

    for port in protocol + other:
        if verbose:
            print(f'Ouverture de {port.device} ({port.description}) ...')
        try:
            ser = open_rc_serial(port.device)
        except Exception as e:
            if verbose:
                print(f'  Impossible : {e}')
            continue
        if verbose:
            print(f'RC-N1 sur {port.device}.')
        return ser
    return None


def find_port(forced=None, verbose=True):
    """Nom du port seulement — sans l'ouvrir (évite de reset l'USB)."""
    if forced:
        return forced
    for port in serial.tools.list_ports.comports(True):
        if is_log_interface(port):
            continue
        if is_protocol_interface(port) or get_dji_vid(port) == DJI_VID:
            if verbose:
                print(f'RC-N1 vue sur {port.device}.')
            return port.device
    return None


def read_state(ser):
    """Demande un paquet sticks, attend jusqu'à 1 s. Pas de spam USB."""
    misses = 0
    while True:
        ser.write(DJI_REQUEST)
        ser.flush()
        b = ser.read(1)
        if not b:
            misses += 1
            if misses > 8:
                raise serial.SerialException(
                    'RC muette (débranchée ou port déjà pris)'
                )
            continue
        misses = 0
        if b != b'\x55':
            continue
        ph = ser.read(2)
        if len(ph) != 2:
            continue
        pl = 0b0000001111111111 & struct.unpack('<H', ph)[0]
        if pl != 38:
            if 4 < pl <= 64:
                ser.read(max(pl - 3, 0))
            continue
        data = b'\x55' + ph + ser.read(pl - 3)
        if len(data) != 38:
            continue
        return {k: parse_input(data[s:e]) for k, (s, e) in FIELDS.items()}


def main():
    ap = argparse.ArgumentParser(description='RC-N1 → UDP (stick + molette)')
    ap.add_argument('port', nargs='?', default=None, help='Port série (ex. COM7 ou /dev/ttyACM0)')
    ap.add_argument('--target', default='127.0.0.1', help='IP de destination UDP (défaut 127.0.0.1)')
    ap.add_argument('--udp-port', type=int, default=7777, help='Port UDP (défaut 7777)')
    ap.add_argument('--live', action='store_true', help='Afficher les valeurs sans envoyer')
    ap.add_argument('--calibrate', action='store_true',
                    help='Lancer la calibration de la RC puis piloter')
    ap.add_argument('--no-calib', action='store_true',
                    help='Ignorer le fichier de calibration')
    ap.add_argument('--deadzone', type=float, default=0.03,
                    help='Zone morte au centre (fraction de la course, défaut 0.03)')
    args = ap.parse_args()

    ser = find_open_serial(args.port)
    if not ser:
        print('RC-N1 introuvable. Câble USB-C du dessous, RC allumée.')
        print('  Si ça se répète : sudo cp dji/99-dji-rc.rules /etc/udev/rules.d/')
        sys.exit(1)
    print(f'Port {ser.port} ouvert.')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.target, args.udp_port)

    # Calibration : demandée explicitement, ou proposée au premier usage.
    calib = None if args.no_calib else load_calib()
    if args.calibrate:
        try:
            calib = run_calibration(ser)
        except serial.SerialException as e:
            print(f'Calibration interrompue : {e}')
            sys.exit(1)
    elif calib is None and not args.no_calib:
        print('Aucune calibration trouvée. Lance « python dji_host.py --calibrate »')
        print('pour un centre parfaitement neutre. (Valeurs par défaut utilisées.)\n')

    print('Lecture des sticks. Ctrl+C pour arrêter.\n')
    last = None
    try:
        while True:
            try:
                st = apply_calib(read_state(ser), calib, args.deadzone)
            except serial.SerialException as e:
                print(f'\nUSB coupé : {e}')
                print('Reconnexion dans 2 s...')
                try:
                    ser.close()
                except Exception:
                    pass
                time.sleep(2.0)
                ser = find_open_serial(args.port)
                if not ser:
                    print('RC-N1 introuvable.')
                    sys.exit(1)
                print(f'Reconnecté sur {ser.port}.')
                continue
            if args.live:
                line = (
                    f"LX={st['lx']:+6d} LY={st['ly']:+6d} "
                    f"RX={st['rx']:+6d} RY={st['ry']:+6d} CAM={st['cam']:+6d}"
                )
                if line != last:
                    last = line
                    print(f"\r{line}   ", end='', flush=True)
            else:
                sock.sendto(json.dumps(st).encode(), target)
    except KeyboardInterrupt:
        print('\nArrêt.')
    finally:
        try:
            ser.close()
        except Exception:
            pass
        sock.close()


if __name__ == '__main__':
    main()
