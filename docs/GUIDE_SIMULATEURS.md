# Guide des simulateurs et outils pour les prochains chapitres

> Ce guide recense les outils de la stack, **quand les utiliser** et **comment les
> faire parler ensemble**, en les reliant aux chapitres du cours (SITL = 2.12,
> MAVLink = 4.7, et les futurs chapitres sur la simulation).

---

## 1. Les outils, un tableau pour s'y retrouver

| Outil | C'est quoi | Tu t'en sers pour | Chapitres liés |
|---|---|---|---|
| **ArduPilot SITL** | le firmware réel, simulé | le cerveau : modes, stabilisation, protections, PID | 2.12, 4.2, 4.4 |
| **Gazebo** | la physique + les capteurs | le corps : gravité, hélices, capteurs simulés | 2.12, 8.2 (futur) |
| **gzclient** (vue 3D) | la fenêtre 3D de Gazebo | **VOIR le drone osciller/vibrer** quand tu règles le PID | 2.6, 2.7, 2.12 |
| **QGroundControl (QGC)** | la station sol graphique | voir le vol en 3D, régler le PID, missions, journaux | 2.12, 4.4, 4.7 |
| **MAVProxy** | la station sol en ligne de commande | automatiser, lire/envoyer des messages MAVLink, scripts | 4.7, 8.1 |
| **pymavlink** | bibliothèque Python MAVLink | lire un `.tlog`, écrire des scripts MAVLink | 4.7.11 |
| **ROS2 CLI** | lignes de commande ROS2 | explorer topics/services, lancer des nœuds | 4.x, 8.1 |
| **rviz2** | visualisation ROS2 (3D) | voir les topics (position, capteurs) — optionnel, besoin d'un écran X | avancé |

> **Règle simple** : ArduPilot *décide*, Gazebo *bouge*, QGC *montre*, et ton code
> (ROS2 / pymavlink) *commande*. Chaque chapitre vient piocher dans cet outillage.

---

## 2. Où brancher quoi

```
        ROS2 (ros conteneur) ── tcp:5760 ──▶ ArduPilot SITL ◀── UDP:14550 ── QGC
                 │                             │
        joy_bridge / flight_control       plugin ardupilot_gazebo
        pid_tuner / ton script              │
                 │                         ▼
                 └──────────────────────▶ Gazebo (physique + capteurs)
```

- **QGC** → connexion **UDP 14550** (le SITL envoie déjà dessus). C'est la fenêtre.
- **MAVROS / tes scripts** → le SITL écoute aussi en **TCP 5760** (dans le réseau
  Docker, le nom du service est `sim`).
- **Gazebo** ↔ **SITL** → localhost, ports UDP 9002/9003 (même conteneur `sim`).

---

## 3. Utiliser chaque outil

### QGroundControl — le quotidien
1. Démarrer la sim (`scripts\start.bat`).
2. Ouvrir QGC → **Application Settings → Comm Links → UDP 14550 → Connect**.
3. Tu vois le drone connecté. **Setup → Tuning** pour le PID, **Parameters** pour
   tout le reste, l'onglet **Plan** pour une mission de points de passage.

> Le `.tlog` (journal de vol) que produit QGC sert au chapitre 4.7 (lire une tension
> au fil du temps avec `pymavlink`).

### MAVProxy — la console
MAVProxy est le couteau suisse en ligne de commande d'ArduPilot. Pour l'utiliser :

```bash
docker compose exec sim bash -lc "mavproxy.py --master=tcp:127.0.0.1:5760 --out=127.0.0.1:14550"
```

Puis, dans sa console : `mode LOITER`, `arm throttle`, `param show ATC_RAT_PIT_P`,
`param set ATC_RAT_PIT_D 0.0012`... C'est l'outil idéal pour **scriptabiliser** les
essais (chapitre 8.1) et pour comprendre le protocole MAVLink de l'intérieur.

### pymavlink — les journaux (chapitre 4.7)
Dans QGC, enregistre un vol → un fichier `.tlog`. Puis, n'importe où avec Python :

```python
from pymavlink import mavutil
j = mavutil.mavlink_connection("vol.tlog")
while True:
    m = j.recv_match(type="SYS_STATUS", blocking=False)
    if m is None:
        break
    print(m.voltage_battery / 1000.0, "V")   # tension au fil du temps
```

### ROS2 CLI — explorer et lancer
```bash
docker compose exec ros bash -lc "ros2 topic list"       # tout ce qui circule
docker compose exec ros bash -lc "ros2 topic echo /mavros/local_position/pose"
docker compose exec ros bash -lc "ros2 service list"     # les actions possibles
docker compose exec ros bash -lc "ros2 run mon_package mon_noeud_node"
```

### gzclient — LA vue 3D (voir l'oscillation du drone)
C'est la fenêtre que tu veux pour le PID : le modèle 3D du drone **dans la physique
réelle**, qui oscille, vibre et diverge visiblement quand le réglage est mauvais.

```bat
:: Windows : VcXsrv requis (voir INSTALL.md)
scripts\start_gui.bat
:: Linux / WSL2
scripts\start_gui.sh
```

gzclient se connecte à `gzserver` déjà lancé (même conteneur, même master Gazebo).
Bouge la caméra (molette/ctrl-clic) pour bien voir l'attitude. Quand tu divises
`ATC_RAT_PIT_D` par 3, **tu vois le tangage osciller** — c'est le chapitre 2.6 rendu
concret.

### rviz2 — voir les topics en 3D (optionnel, avancé)
rviz2 a besoin d'un écran. Sur Windows avec **VcXsrv** : lancer VcXsrv, définir
`DISPLAY=127.0.0.1:0`, puis `docker compose exec ros bash -lc "rviz2"`. Utile pour
visualiser les capteurs, les repères TF, les consignes ROS2.

---

## 4. Modifier Gazebo : monde, modèle, capteurs

### Choisir le drone : iris ou X500
Deux drones sont disponibles, sélectionnables dans `.env` :
- **iris** (défaut) : fourni par `ardupilot_gazebo`, ~1,5 kg, gains PID par défaut.
- **X500** (notre modèle, `sim/models/x500`) : classe 500 mm, **~2 kg**, inertie plus
  grande → **gains PID différents** (chapitre 2.9 : gains ∝ inertie). Décommenter
  `WORLD=/sim/worlds/x500_runway.world` dans `.env` puis relancer le conteneur `sim`.

C'est l'expérience idéale pour montrer que **le même firmware ne se règle pas de la
même façon sur deux drones différents**.

### Le monde actuel
Le monde chargé par défaut est fourni par le plugin `ardupilot_gazebo` :
`iris_arducopter_runway.world` (une piste, l'iris quad). Le fichier `.world` décrit
**le décor et les objets**, le modèle `.sdf` décrit **le drone**.

### Ajouter des obstacles dans le monde
Dans `sim/worlds/mon_monde.world`, tu peux ajouter des boîtes, des murs, des cônes :

```xml
<sdf version="1.6">
  <world name="default">
    <include>                    <!-- le drone iris + le plugin ArduPilot -->
      <uri>model://iris_arducopter</uri>
      <name>iris</name>
    </include>
    <model name="mur">
      <static>true</static>
      <pose>5 0 0 0 0 0</pose>   <!-- à 5 m devant le départ -->
      <link name="link">
        <collision name="collision"><box><size>0.5 4 3</size></box></collision>
        <visual name="visual"><box><size>0.5 4 3</size></box>
          <material><ambient>0.8 0.2 0.2 1</ambient></material></visual>
      </link>
    </model>
  </world>
</sdf>
```

Puis charger ton monde : mettre `WORLD=/sim/worlds/mon_monde.world` dans `.env` et
relancer le conteneur `sim`. C'est comme ça qu'on prépare un TP d'évitement réel
(des murs, et le télémètre du chapitre 6).

### Ajouter un capteur (télémètre) au drone
Pour que l'évitement fonctionne avec une **vraie** mesure, il faut ajouter un capteur
au modèle `iris` et le faire remonter à ArduPilot via le plugin. Principe :
1. Dans le modèle `.sdf`, ajouter un `<sensor type="ray">` (ou `gpu_ray` pour un Lidar)
   orienté vers l'avant, avec une portée (ex. 10 m).
2. Configurer le plugin `ArduPilotPlugin` pour mapper ce capteur vers le message
   MAVLink `DISTANCE_SENSOR` (paramètres `RNGFND*` d'ArduPilot) ou vers un topic ROS2.
3. ArduPilot publie alors `/mavros/rangefinder/rangefinder`, que ton script lit.

> C'est de niveau avancé : commence par tester l'évitement avec `ros2 topic pub`
> (voir `ECRIRE_SES_SCRIPTS.md`, section 6.1), puis branche le vrai capteur ensuite.
> Références : README de `ardupilot_gazebo`, doc ArduPilot « Rangefinder » et
> « Proximity sensor ».

---

## 5. Les prochains chapitres et l'outillage qu'ils demandent

| Futur chapitre (corpus) | Sujet | Outil à utiliser |
|---|---|---|
| **8.1** | SITL comme outil de test systématique : automatiser des essais, rejouer des journaux | MAVProxy + `pymavlink` + scripts ROS2 (test automatisés) |
| **8.2** | Simulation 3D avec capteurs de perception | Gazebo (capteurs `ray`/`gpu_ray`, caméra) + ROS2 + rviz2 |
| **8.3** | Simulation matérielle en boucle (HIL) | nécessite un vrai flight controller (hors Docker) |
| Module 4 | Firmware, MAVLink, télémétrie | `pymavlink`, MAVProxy, QGC (journaux) |

**Ce que notre stack couvre déjà** : 8.1 (tout est scriptable) et 8.2 (Gazebo peut
porter des capteurs). 8.3 demandera du matériel, en dehors de Docker.

---

## 6. Références utiles

- ArduPilot SITL : <https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html>
- ArduPilot-Gazebo : <https://github.com/ArduPilot/ardupilot_gazebo>
- QGroundControl : <https://qgroundcontrol.com/>
- MAVROS (wiki) : <https://github.com/mavlink/mavros>
- pymavlink : <https://github.com/ArduPilot/pymavlink>
