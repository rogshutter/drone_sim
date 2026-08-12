# Drone-SIM — Gazebo + ArduPilot + ROS2 (apprentissage du PID)

Environnement de simulation **tout-en-un pour Docker** : chaque étudiant clone ce
dépôt, lance `docker compose up -d --build`, et pilote un drone simulé avec sa
**télécommande DJI RC-N1**, en réglant les **gains PID** en direct et en observant
le comportement **en 3D** (Gazebo Harmonic / RViz) et dans **QGroundControl**.

Stack moderne et durable : **Ubuntu 24.04 + ROS2 Jazzy + Gazebo Harmonic +
ardupilot_gz** (le plugin officiel ArduPilot).

```
RC-N1 ──USB──▶ dji_host.py (host) ──UDP 7777──▶ joy_bridge ──/joy──▶ flight_control
                                                                       │
                                                 /mavros/rc/override    ▼
ROS2 Jazzy ◀──MAVROS localhost:5760──▶ ArduPilot SITL ──(ardupilot_gz)──▶ Gazebo Harmonic
                                                                           │
QGroundControl (host) ◀──MAVLink──▶ SITL                       + RViz (vue 3D) + réglage PID
```

## Service (docker compose)

| Service | Rôle | Détails |
|---|---|---|
| `sim` | **Tout en un** : SITL + Gazebo Harmonic + RViz + MAVROS + nodes | Un seul conteneur (le stack moderne est un seul workspace ROS2). `joy_bridge` (UDP→Joy), `flight_control` (Joy→RC override), `pid_tuner` (ROS2→PID) |

## Dossiers

- `dji/` — script hôte (Windows/Linux) : lit la RC-N1 et envoie les sticks en UDP
- `ros/src/` — packages ROS2 (joy_bridge, flight_control, pid_tuner, obstacle_avoid, drone_launch)
- `sim/` — Dockerfile (Jazzy+Harmonic+ardupilot_gz+SITL), workspace, modèles (dont **X500**)
- `scripts/` — lanceurs 1-clic (`start.bat` / `start.sh`, `stop`, `run_dji`)
- `docs/` — toute la documentation :
  - `GUIDE_PAS_A_PAS.md` — **le guide de démarrage complet (étape par étape, pour l'encadrant)**
  - `GUIDE_DEBUTANT.md` — le système expliqué de zéro (débutant)
  - `ECRIRE_SES_SCRIPTS.md` — écrire ses propres scripts ROS2 (évitement d'obstacles)
  - `GUIDE_SIMULATEURS.md` — les simulateurs/outils pour les prochains chapitres
  - `INSTALL.md` — installation poste étudiant
  - `TP_PID.md` — le TP de réglage PID

## Démarrage rapide (Windows)

```bat
:: 1) installer les prérequis (voir docs/INSTALL.md)
scripts\start.bat
:: 2) ouvrir QGroundControl -> lien MAVLink (voir INSTALL.md)
scripts\start_gui.bat       :: (optionnel) VUE 3D : RViz/Gazebo
scripts\run_dji.bat         :: (optionnel) piloter avec la RC-N1
:: 3) dans QGC : armer, décoller, voler
::    -> règle le PID et OBSERVE l'oscillation en 3D
```

## Réglage du PID (2 façons)

1. **QGroundControl** (Setup → Tuning) : modifier `ATC_RAT_PIT_P/I/D`, `ATC_ANG_PIT_P`, …
   → voir le drone réagir en direct.
2. **ROS2** (pédagogique) :
   ```bash
   docker compose exec sim bash -lc \
     "ros2 param set /pid_tuner ATC_RAT_PIT_D 0.0012"
   ```

Le TP complet (aligné sur les chapitres 2.7 / 2.12 du cours) est dans `docs/TP_PID.md`.

## Versions figées

- Ubuntu **24.04**, ROS2 **Jazzy**, Gazebo **Harmonic**, plugin **ardupilot_gz**
- ArduPilot **Copter-4.5.7** (modifiable dans `.env`)
- Miroir apt ROS2 configurable via `ROS2_APT_MIRROR` dans `.env` (si
  `packages.ros.org` est bloqué — réseaux RDC — utiliser ex. Huawei Cloud)
- Modèles : **iris** (défaut) et **X500** (`sim/models/x500`, 500 mm / ~2 kg)

> Principe du cours : *on règle en simulation avant le matériel — un mauvais gain
> en simulation coûte une minute, sur un appareil réel il casse du matériel.*
