# Pilotage façon DJI — décollage et arrêt par geste « V »

Ce document explique comment on pilote le drone simulé **comme avec une DJI** :
les sticks pilotent directement, et un **geste « V »** (le CSC de DJI) sert à
**décoller** et à **arrêter**.

Tout est géré par le node `flight_control`
(`ros/src/flight_control/flight_control/flight_control_node.py`), qui reçoit les
sticks (`/joy`) et parle à l'autopilote via **MAVROS**.

---

## 1. Le geste « V » (comme DJI)

Sur une DJI, on démarre les moteurs avec le **CSC** : les **deux sticks poussés
vers le bas et l'un vers l'autre** (coins intérieurs) — ça dessine un « V ».

Ici, même principe, maintenu **~1,2 s** :

```
   Stick GAUCHE          Stick DROIT
       \                    /
        \                  /
         v                v          <- les deux vers le BAS
      (vers la droite) (vers la gauche)   ... et l'un vers l'AUTRE
```

Le geste a **deux effets selon l'état** (exactement comme le CSC DJI qui
démarre ET coupe les moteurs) :

| État du drone | Geste « V » | Effet |
|---|---|---|
| **Au sol** (désarmé) | maintenir ~1,2 s | **Arme + décolle** à `takeoff_alt` (2,5 m), puis passe en `LOITER` |
| **En vol** | maintenir ~1,2 s | **Atterrit** (mode `LAND`) puis se désarme tout seul |

> Un délai anti-rebond (`gesture_cooldown_s`, 3 s) évite les double-déclenchements.

---

## 2. Ce qui se passe au décollage

Séquence automatique (non bloquante), pilotée par l'état réel de l'autopilote :

1. `GUIDED` (mode nécessaire pour un décollage commandé)
2. `arm` (armement des moteurs)
3. `takeoff` jusqu'à `takeoff_alt`
4. une fois l'altitude atteinte → **`LOITER`** : les sticks reprennent la main,
   façon DJI (tenue de position GPS, lâcher les sticks = vol stationnaire).

Sécurité : après le passage en `LOITER`, l'override des sticks ne s'active
qu'une fois le **stick de gaz recentré** — sinon le geste « V » (gaz en bas)
ferait redescendre le drone immédiatement.

---

## 3. Pilotage en vol (Mode 2, comme DJI)

| Stick | Axe | Action |
|---|---|---|
| Gauche vertical | `ly` | Gaz / montée-descente |
| Gauche horizontal | `lx` | Rotation (lacet) |
| Droit vertical | `ry` | Avant / arrière (tangage) |
| Droit horizontal | `rx` | Gauche / droite (roulis) |

En `LOITER`, stick centré = **vol stationnaire** (le drone tient sa position),
comme une DJI.

---

## 4. Arrêter

- **En vol** : refais le geste « V » → le drone passe en `LAND`, se pose et se
  **désarme automatiquement** au sol.
- **Au sol après atterrissage** : rien à faire, il est déjà désarmé.

---

## 5. Calibration de la RC (avant de piloter)

Un centre qui dérive ferait avancer le drone tout seul et déclencherait mal le
geste « V ». On calibre donc la RC **avant** de commencer.

Au **premier** `run_dji`, la calibration se lance automatiquement. Sinon :

```bash
python dji/dji_host.py --calibrate
```

Deux étapes :
1. **Centre** : lâcher tous les sticks, ne rien toucher (mesure ~2 s).
2. **Butées** : bouger tous les sticks ET la molette dans toutes les directions
   pendant 6 s.

Le résultat (centre + butées réels par axe) est sauvé dans `dji/rc_calib.json`
et réappliqué à chaque lancement : le **centre est ramené à 0**, la **pleine
course à ±32767**, avec une **zone morte** au centre (option `--deadzone`, défaut
0,03). La RC utilisée ici sort déjà en ±32767 / centre 0 ; la calibration corrige
surtout la petite dérive du centre et les butées réelles de chaque axe.

---

## 6. Prérequis simulateur

- Les modes `GUIDED` et `LOITER` ont besoin d'une **position estimée** (GPS +
  EKF). En SITL c'est fourni, mais il faut **attendre ~30 s** après le démarrage
  que l'EKF soit prêt, sinon l'armement est refusé (message dans les logs).
- MAVROS doit être connecté au SITL (topic `/mavros/state` avec `connected: true`).
  Vérifier : `docker compose exec sim bash -lc "ros2 topic echo /mavros/state --once"`.

---

## 7. Réglages (paramètres ROS2)

Modifiables à chaud, ex. :

```bash
docker compose exec sim bash -lc "ros2 param set /flight_control takeoff_alt 3.0"
docker compose exec sim bash -lc "ros2 param set /flight_control fly_mode ALT_HOLD"
```

| Paramètre | Défaut | Rôle |
|---|---|---|
| `takeoff_alt` | `2.5` | Altitude de décollage (m) |
| `fly_mode` | `LOITER` | Mode de vol après décollage (`LOITER` = tenue GPS façon DJI ; `ALT_HOLD` = tenue d'altitude sans GPS) |
| `gesture_hold_s` | `1.2` | Durée de maintien du geste « V » |
| `gesture_cooldown_s` | `3.0` | Anti-rebond entre deux gestes |
| `v_down_thresh` | `0.85` | Seuil « stick vers le bas » |
| `v_side_thresh` | `0.6` | Seuil « stick sur le côté » |

---

## 8. Réglage / dépannage du geste

Le geste est **robuste au signe** (peu importe quel côté est « positif » sur ta
radio) : il exige seulement les deux verticaux en butée basse **et** les deux
horizontaux en butée de **signes opposés** (la forme en V).

**Voir les valeurs des sticks en direct** (pour régler les seuils) :

```bash
python dji/dji_host.py --live
```

- Le geste ne se déclenche **jamais** → baisse `v_down_thresh` / `v_side_thresh`
  (ex. 0,7 / 0,5), ou vérifie avec `--live` que les sticks atteignent bien les
  butées.
- Le geste se déclenche **trop facilement** → monte les seuils, ou augmente
  `gesture_hold_s`.
- Décollage refusé → EKF/GPS pas prêt (attendre), ou pré-arm ArduPilot en échec
  (voir les logs `flight_control` et `mavros`).

---

## 9. Comparaison avec le repo PX4 de référence

Ce pilotage s'inspire de
[MechaMind-Labs/ROS2-PX4_Drone_Teleoperation_Using_Joystick](https://github.com/MechaMind-Labs/ROS2-PX4_Drone_Teleoperation_Using_Joystick),
adapté à **ArduPilot** :

| | Repo PX4 (référence) | Ici (ArduPilot) |
|---|---|---|
| Contrôle | Vitesse `OFFBOARD` (setpoints) | **RC override** (sticks directs, plus proche d'une vraie radio DJI) |
| Décollage | Bouton A (arm) | **Geste « V »** façon DJI |
| Arrêt | Bouton Y (disarm) | **Geste « V »** en vol → `LAND` |
| Tenue de position | OFFBOARD | **`LOITER`** (tenue GPS, lâcher = stationnaire) |

> Le modèle **x500** de la référence vient de PX4. Pour l'avoir en ArduPilot,
> il faut le modèle x500 de `ardupilot_gazebo` (changement de monde/modèle) —
> voir la note dans le README.
