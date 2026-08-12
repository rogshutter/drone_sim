#!/usr/bin/env python3
"""Sonde la RC-N1 : verifie que les ports repondent au protocole DJI."""
import serial
import time

R = bytearray.fromhex('55 0d 04 33 0a 06 eb 34 40 06 01 74 24')

for p in ['/dev/ttyACM0', '/dev/ttyACM1']:
    try:
        s = serial.Serial(port=p, timeout=0.5)
    except Exception as e:
        print(p, '->', 'ouverture impossible:', e)
        continue
    # 1) la RC emet-elle toute seule ?
    time.sleep(1)
    n1 = s.in_waiting
    d1 = s.read(n1)
    # 2) reponse apres la requete DJI ?
    s.write(R)
    time.sleep(1)
    n2 = s.in_waiting
    d2 = s.read(n2)
    s.close()
    print(p, '-> seul:', len(d1), 'octets:', d1[:16].hex())
    print(p, '-> apres requete:', len(d2), 'octets:', d2[:16].hex())
