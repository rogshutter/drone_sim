# Guide d'installation — poste étudiant (Windows)

Objectif : en ~30 min, faire voler un drone simulé piloté par la RC-N1, avec
réglage du PID en direct.

## 1. Prérequis

| Logiciel | Pourquoi | Où |
|---|---|---|
| **Docker Desktop** | Exécute Gazebo + ArduPilot + ROS2 dans des conteneurs | <https://www.docker.com/products/docker-desktop/> (back-end WSL2 par défaut) |
| **Git** | Cloner le dépôt | <https://git-scm.com/> |
| **Python 3** | Lire la RC-N1 sur le host (script `dji_host.py`) | <https://www.python.org/downloads/> |
| **QGroundControl** | Vue 3D du vol + réglage PID | <https://qgroundcontrol.com/> (installeur Windows) |

> Windows 11 : Docker Desktop gère tout. Pas besoin d'installer Linux.

## 2. Télécharger le projet

```bat
git clone <URL-de-votre-dépôt> drone-sim
cd drone-sim
pip install -r dji\requirements.txt
```

## 3. Premier lancement

```bat
scripts\start.bat
```

Docker Desktop doit être démarré. `start.bat` **télécharge l'image pré-construite**
(publiée sur ghcr.io) : quelques minutes selon la connexion, pas de compilation.
Les lancements suivants sont immédiats.

> Si l'image pré-construite n'est pas disponible (dépôt privé, ou pas encore
> publiée), `start.bat` **construit l'image localement** en repli : **10 à 30 min**
> selon la machine et le réseau. Pour forcer une reconstruction locale :
> `set REBUILD=1` avant `scripts\start.bat`.

Vérifier que le conteneur tourne :

```bat
docker compose ps
```

Vous devez voir **`drone-sim`** en statut `Up` (un seul conteneur : SITL + Gazebo
+ ROS2 + MAVROS + nodes y tournent ensemble).

## 4. Piloter avec la RC-N1

1. Connecter la DJI RC-N1 par le **port USB-C du dessous** (entre les supports de sticks).
2. Allumer la RC.
3. Lancer le script :
   ```bat
   scripts\run_dji.bat
   ```
   → le script détecte le port, envoie les sticks au conteneur ROS2 (UDP 7777).

## 5. Voir le vol et régler le PID (QGroundControl)

1. Ouvrir **QGroundControl**.
2. Application Settings → Comm Links → **Ajouter** un lien :
   - Type : **UDP**, Listening Port : **14550** (l'autopilote simulé y envoie déjà)
   - Appuyer sur **Connect**.
3. Le drone simulé (iris) apparaît, connecté, mode **Stabilize**.
4. **Setup → Tuning** : modifier les gains PID (ex. `ATC_RAT_PIT_D`) et observer
   l'effet immédiat dans la vue.

> Alternative 3D : Gazebo rend la physique en arrière-plan. Pour une fenêtre 3D,
> installer **VcXsrv** (serveur X Windows) puis relancer avec
> `set DISPLAY=127.0.0.1:0` avant `scripts\start.bat`, et exécuter `docker compose exec sim gzclient`.

## 6. Voir le drone en 3D (recommandé — pour voir l'oscillation)

QGC affiche la carte (2D). Pour **voir le drone osciller / vibrer en 3D** quand tu
règles le PID, on utilise **Gazebo** (`gzclient`), qui rend la physique en temps réel.

Sous Windows, il faut un petit serveur X : **VcXsrv** (gratuit).
1. Installer VcXsrv : <https://sourceforge.net/projects/vcxsrv/>
2. Lancer la simulation : `scripts\start.bat`
3. Ouvrir la vue 3D : `scripts\start_gui.bat`

Une fenêtre 3D s'ouvre : le drone iris dans le monde simulé.
- **Règle un PID mal** (ex. `ATC_RAT_PIT_D` divisé par 3 dans QGC) → le drone
  **oscille visiblement** dans la vue 3D.
- La vue 3D **complète QGC** : QGC pour les paramètres/courbes, Gazebo pour le
  comportement physique concret.

> Linux / WSL2 : rien à installer, `scripts/start_gui.sh` suffit (WSLg affiche la
> fenêtre). Si la fenêtre est noire, essayer `export LIBGL_ALWAYS_SOFTWARE=1`.

## GPU ou CPU (rendu 3D)

Le simulateur détecte automatiquement le matériel — **rien à configurer** :

| Machine | Rendu 3D | Détail |
|---|---|---|
| **Windows** (Docker Desktop) | **CPU** (software) | L'accélération GPU OpenGL de Gazebo n'est pas disponible sous Docker Desktop. Le CPU suffit largement pour le TP PID. |
| **Linux sans GPU NVIDIA** | **CPU** (software) | Fonctionne partout. |
| **Linux + GPU NVIDIA** | **GPU** (matériel) | Activé automatiquement par `start.sh` si `nvidia-smi` **et** le [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) sont présents. |

> La **physique** (SITL, le PID) tourne sur CPU dans tous les cas ; le GPU
> n'accélère que la **vue 3D**. Une machine sans GPU fait tourner le TP sans souci.

## 7. Arrêter

```bat
scripts\stop.bat
```

## Dépannage

- **`docker compose ps` montre un conteneur redémarrant** : attendre ~20 s au premier
  démarrage (le SITL attend le plugin Gazebo, MAVROS attend le SITL).
- **QGC ne voit pas le drone** : vérifier que le lien UDP est sur le port **14550**
  et que `docker compose ps` montre `drone-sim` en `Up`.
- **`dji_host.py` ne trouve pas la RC** : câble USB-C capable de transfert de données,
  port du dessous, RC allumée, DJI Assistant 2 **fermé**.
- **Changer la version d'ArduPilot** : modifier `ARDUPILOT_VERSION` dans `.env`,
  puis `docker compose build sim`.
