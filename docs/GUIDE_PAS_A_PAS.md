# Guide de démarrage pas-à-pas (pour toi, l'encadrant)

> Ton objectif : aller de **zéro** jusqu'à **piloter un drone simulé en 3D, régler
> son PID et voir l'oscillation**, en comprenant chaque étape pour pouvoir
> l'enseigner. Suis les étapes dans l'ordre. À chaque étape, il y a un **point de
> contrôle** (ce que tu DOIS voir) et une **astuce d'enseignant** (💡).

---

## Vue d'ensemble — ce que tu vas faire en 10 étapes

```
 1. Installer les outils          (Docker, Git, Python, QGC, VcXsrv)
 2. Récupérer le projet           (drone-sim)
 3. Tester la RC-N1               (le script qui lit la télécommande)
 4. Construire la simulation      (docker compose build — 10 à 30 min)
 5. Vérifier que tout tourne      (conteneurs + QGC + MAVROS)
 6. Piloter le drone              (RC-N1 ou clavier : décoller, voler)
 7. Voir le drone en 3D           (gzclient — l'oscillation devient visible)
 8. Régler le PID                 (QGC ou ROS2, en regardant la 3D)
 9. Écrire tes premiers scripts   (optionnel — pour les curieux)
10. Arrêter / redémarrer / dépanner
```

Règle d'or tout au long : **chaque étape a un point de contrôle.** Tu ne passes à la
suivante que quand tu as vu ce qui est attendu. Si un point de contrôle ne se vérifie
pas, c'est là qu'il faut me poser la question — pas après.

---

## Étape 1 — Installer les outils

Ce qu'il faut sur le poste (une fois pour toutes, ~20 min) :

| Outil | Pourquoi | Lien | Vérification |
|---|---|---|---|
| **Docker Desktop** | exécute Gazebo + ArduPilot + ROS2 | <https://www.docker.com/products/docker-desktop/> | `docker --version` et `docker compose version` |
| **Git** | cloner / mettre à jour le projet | <https://git-scm.com/> | `git --version` |
| **Python 3** | lire la RC-N1 (script hôte) | <https://www.python.org/downloads/> | `python --version` |
| **QGroundControl** | station sol : params, courbes, log | <https://qgroundcontrol.com/> | l'appli s'ouvre |
| **VcXsrv** (Windows seulement) | afficher la vue 3D Gazebo | <https://sourceforge.net/projects/vcxsrv/> | VcXsrv se lance |

**Point de contrôle** : ouvres un terminal, `docker --version` répond, `python --version`
répond (3.x).

**⚠️ Windows** : Docker Desktop doit être **démarré** (l'icône baleine dans la barre
des tâches doit être verte). Il s'appuie sur WSL2 (auto-installé).

💡 **Aux étudiants** : explique leur que Docker est « une boîte qui contient le
simulateur complet » — eux n'installent QUE les 5 outils, pas ROS2 ni Gazebo à la main.

---

## Étape 2 — Récupérer le projet

Sur ce poste il est déjà dans `D:\Drone\drone-sim`. Pour une autre machine :

```bat
git clone <URL-de-ton-dépôt> drone-sim
cd drone-sim
```

L'arborescence (à connaître par cœur) :

```
drone-sim/
├── docker-compose.yml    ← déclare les 2 conteneurs (sim, ros)
├── .env                  ← version d'ArduPilot (figée)
├── dji/dji_host.py       ← script qui lit la RC-N1 et envoie en UDP
├── ros/src/…             ← les nodes ROS2 (joy, contrôle, PID, obstacle)
├── sim/…                 ← l'image Gazebo + ArduPilot
├── scripts/              ← start.bat, start_gui.bat, run_dji.bat, stop.bat
└── docs/                 ← toute la doc (dont ce guide)
```

**Point de contrôle** : `ls` montre ces dossiers.

---

## Étape 3 — Tester la RC-N1 (avant de lancer la simulation)

Le script `dji/dji_host.py` lit la télécommande et envoie les sticks sur le réseau.
On le teste d'abord seul, pour vérifier que la RC est reconnue **avant** de compliquer.

```bat
cd D:\Drone\drone-sim\dji
pip install -r requirements.txt
```

1. **Brancher la RC-N1** par le **port USB-C du DESSOUS** (entre les supports de sticks).
2. Allumer la RC.
3. Lancer en mode « live » (affiche les valeurs sans envoyer) :
   ```bat
   python dji_host.py --live
   ```

**Point de contrôle** : la console affiche `LX= ... LY= ... RX= ... RY= ... CAM= ...`
et **les nombres changent quand tu bouges les sticks**. `LX/LY` = stick gauche
(roulis/tangage), `RX/RY` = stick droit (lacet/gaz), `CAM` = molette. `Ctrl+C` pour
arrêter.

**⚠️ Si « RC-N1 introuvable »** : câble capable de transférer des données, port du
dessous, RC allumée, DJI Assistant 2 fermé.

💡 **Aux étudiants** : ce script est **le même sur Windows et Linux** (réponse à ta
question : oui, il marche sur Linux, `/dev/ttyACM0` au lieu de `COMx`).

---

## Étape 4 — Construire la simulation (10-30 min la première fois)

```bat
cd D:\Drone\drone-sim
scripts\start.bat
```

Ce que ça fait (et ce qui se passe dans les coulisses) :
1. Vérifie/attend Docker Desktop.
2. `docker compose up -d --build` → **construit les 2 images** :
   - `sim` : installe Gazebo Classic 11, compile le plugin `ardupilot_gazebo`, puis
     **compile le firmware ArduPilot SITL** (version figée `Copter-4.5.7`). C'est le
     plus long (10-20 min).
   - `ros` : installe ROS2 Humble + MAVROS, compile les nodes.
3. Démarre les 2 conteneurs.

**Point de contrôle** : le build se termine sans erreur et les conteneurs tournent.
Pour vérifier :

```bat
docker compose ps
```
→ tu dois voir `drone-sim` et `drone-ros` en **Up**.

**⚠️ Premier build long** : normal. Les fois suivantes, c'est immédiat (les images
sont en cache). **⚠️ Le build a besoin d'internet** (télécharge Ubuntu, Gazebo,
ArduPilot…).

💡 **Aux étudiants** : c'est ici qu'ils comprennent la différence entre « build »
(une fois, long) et « up » (rapide). Le build compile le VRAI firmware ArduPilot —
c'est le chapitre 2.12 rendu concret.

---

## Étape 5 — Vérifier que tout tourne

Au démarrage, il y a un ordre à respecter (le SITL attend le plugin Gazebo, MAVROS
attend le SITL). Attends ~30 s après `start.bat`, puis :

```bat
:: les 2 conteneurs sont Up ?
docker compose ps
:: le conteneur sim : Gazebo + SITL démarrent sans erreur ?
docker compose logs sim --tail 30
:: le conteneur ros : MAVROS s'est connecté au SITL ?
docker compose logs ros --tail 30
```

**Point de contrôle** : dans `logs sim`, tu vois `ArduPilot SITL` démarré ; dans
`logs ros`, MAVROS connecté (pas de « connection failed » en boucle).

Puis ouvre **QGroundControl** → Application Settings → Comm Links → **Ajouter** un
lien UDP port **14550** → **Connect**.

**Point de contrôle** : QGC affiche un drone connecté, mode **Stabilize**, avec ses
paramètres. Si QGC ne voit rien, vérifie que `drone-sim` est `Up`.

---

## Étape 6 — Piloter le drone

Deux façons de piloter : la **RC-N1** (la plus parlante) ou le **clavier/souris**
(dépannage rapide).

### Avec la RC-N1
```bat
scripts\run_dji.bat
```
Le script détecte la RC et envoie les sticks au conteneur ROS2 (UDP 7777), qui les
transforme en commandes RC pour ArduPilot.

Dans QGC :
1. Le drone est en **Stabilize**. **Arme** (bouton Arm dans QGC).
2. Pousse doucement le gaz au milieu → le drone monte. Dose pour tenir ~1 m.
3. **Vérifie dans QGC que l'attitude répond** aux sticks.

**Point de contrôle** : le drone décolle, se stabilise, et réagit aux sticks.

### Au clavier (si pas de RC sous la main)
QGC : mode **Stabilize**, armer, puis utiliser le clavier (Q/W/E/A/S/D + gaz) — QGC
a un contrôle clavier intégré. C'est pratique pour les démos rapides.

**⚠️ La commande n'est active qu'après la première entrée de la manette** (petite
sécurité du node `flight_control`) : bouge un stick après le décollage.

💡 **Aux étudiants** : c'est ici le **Mode 1 (manuel)** du guide débutant : toi =
pilote, la RC = commandes, ArduPilot = stabilise. On mettra le Mode 2 (autonome) à
l'étape 9.

---

## Étape 7 — Voir le drone en 3D

C'est LE point que tu voulais : voir l'oscillation **en 3D physique**.

```bat
:: Windows : VcXsrv doit être installé (étape 1)
scripts\start_gui.bat
```

**Point de contrôle** : une fenêtre 3D s'ouvre avec le drone iris posé dans le monde.
Tu peux tourner la caméra (molette = zoom, clic glisser = rotation).

**⚠️ Fenêtre noire/absente** : VcXsrv pas lancé → relancer `start_gui.bat` (il le
lance tout seul). Sur Linux/WSL2 : `scripts\start_gui.sh`, rien à installer.

💡 **Aux étudiants** : QGC = les courbes et les paramètres (le « théorique »), Gazebo
3D = le comportement physique (le « concret »). Les deux ensemble = la compréhension.

---

## Étape 8 — Régler le PID en regardant la 3D

C'est le cœur du TP (voir `docs/TP_PID.md`). Le drone doit être en **Altitude Hold**
(maintien d'altitude) pour observer proprement.

**Expérience n°1 — l'oscillation** (reprise de 2.12.8) :
1. Dans QGC → Setup → Tuning, note la valeur de `ATC_RAT_PIT_D`.
2. **Divise-la par 3** et applique.
3. Pousse un peu l'avant (tangage) et relâche. **Regarde la vue 3D** : le drone
   **oscille en tangage** — il ne s'arrête plus.
4. **Remets la valeur d'origine.** L'oscillation disparaît.

**Expérience n°2 — la vivacité** :
1. **Multiplie `ATC_ANG_PIT_P` par 2** et applique.
2. Refais une petite manœuvre. **Regarde la 3D** : le drone réagit plus vite et
   **dépasse** un peu avant de se stabiliser.
3. Remets la valeur.

**Point de contrôle** : tu as VU le drone osciller puis se stabiliser, en direct, en
changeant deux nombres. C'est le chapitre 2.7/2.6 rendu concret.

**Voie ROS2 (pour les curieux)** :
```bat
docker compose exec sim bash -lc "ros2 param set /pid_tuner ATC_RAT_PIT_D 0.0012"
```

💡 **Aux étudiants** : « on ne règle pas un PID sur un appareil réel — un mauvais
gain casse du matériel. On le règle ici, en simulation, et on VOIT pourquoi. »

---

## Étape 9 — Écrire tes premiers scripts (optionnel, curieux)

Pour aller plus loin (évitement d'obstacles, missions) — voir `docs/ECRIRE_SES_SCRIPTS.md`.

Test rapide de l'exemple fourni :
```bat
:: dans un terminal
docker compose exec sim bash -lc "ros2 run obstacle_avoid obstacle_avoid_node"
:: puis, dans un 2e terminal, simule un obstacle proche :
docker compose exec sim bash -lc "ros2 topic pub -r 10 /range/forward sensor_msgs/msg/Range '{range: 1.0}'"
```

**Point de contrôle** : dans les logs du nœud, tu vois « Obstacle à 1.00 m -> recul ».
C'est le **Mode 2 (autonome)** : un programme décide à la place du pilote.

💡 **Aux étudiants** : c'est exactement la différence manuel/autonome du guide
débutant. Le fichier `obstacle_avoid` est leur point de départ pour leurs propres
scripts.

---

## Étape 10 — Arrêter, redémarrer, dépanner

```bat
:: arrêter la simulation (les conteneurs)
scripts\stop.bat
:: redémarrer (rapide, images en cache)
scripts\start.bat
:: tout reconstruire de zéro (en cas de problème)
docker compose build --no-cache
```

| Symptôme | Cause probable | Solution |
|---|---|---|
| `docker compose ps` montre un conteneur en redémarrage | ordre de démarrage | attendre 30 s, MAVROS se reconnecte tout seul |
| QGC ne voit pas le drone | mauvais port | lien UDP **14550**, `drone-sim` en Up |
| `dji_host.py` ne trouve pas la RC | câble / port / allumage | câble données, port du dessous, RC allumée |
| Vue 3D noire | VcXsrv pas lancé | relancer `start_gui.bat` |
| ROS2 ne démarre pas | SITL pas prêt | `docker compose logs sim` pour voir l'état |

---

## Récap' des commandes essentielles

```bat
scripts\start.bat         :: lancer la simulation (build la 1re fois)
scripts\run_dji.bat       :: piloter avec la RC-N1
scripts\start_gui.bat     :: ouvrir la vue 3D
scripts\stop.bat          :: arrêter
docker compose ps         :: état des conteneurs
docker compose logs sim   :: logs de Gazebo + SITL
docker compose logs ros   :: logs de ROS2/MAVROS
```

## Carte des docs

| Fichier | À quel moment |
|---|---|
| `GUIDE_PAS_A_PAS.md` (celui-ci) | ton fil rouge |
| `INSTALL.md` | la version « étudiant » de ce guide |
| `GUIDE_DEBUTANT.md` | le modèle mental (les 2 modes) |
| `TP_PID.md` | le TP de réglage PID (2h) |
| `ECRIRE_SES_SCRIPTS.md` | écrire ses propres nodes ROS2 |
| `GUIDE_SIMULATEURS.md` | les outils pour les chapitres suivants |
