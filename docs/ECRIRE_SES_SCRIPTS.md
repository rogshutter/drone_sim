# Écrire ses propres scripts (évitement d'obstacles, missions...)

> Tu as compris les deux modes (guide débutant). Ici on passe à la pratique :
> créer un nœud ROS2 qui **pilote le drone tout seul**. On prend l'exemple de
> l'évitement d'obstacles, qui est le point de départ de toute l'autonomie.

---

## 1. Ce qu'il te faut savoir avant d'écrire

Un nœud ROS2 est un **programme Python** qui fait trois choses :
1. il **s'abonne** à des topics pour recevoir des données (où est le drone, distance d'un obstacle...),
2. il **calcule** une décision (tourner à gauche, reculer, avancer...),
3. il **publie** une consigne (vitesse, position...) vers l'autopilote.

Tout se passe dans le conteneur `ros`, mais tes fichiers sont **sur ton disque**
(dossier `ros/src`) : le dossier est monté en volume, donc tu modifies, tu redémarres
le conteneur, et c'est pris en compte — **sans reconstruire l'image Docker**.

---

## 2. Le catalogue MAVROS — les topics que tu peux lire et commander

Grâce à MAVROS, ArduPilot est accessible comme des topics ROS2 standard. Voici les
principaux (à connaître par cœur, ce sont tes « organes »).

### Lire l'état du drone (s'abonner)

| Topic | Type | Ce que c'est |
|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | mode courant (`custom_mode`), armé (`armed`) |
| `/mavros/local_position/pose` | `geometry_msgs/PoseStamped` | position + orientation (repère local) |
| `/mavros/local_position/velocity` | `geometry_msgs/TwistStamped` | vitesse linéaire + angulaire |
| `/mavros/imu/data` | `sensor_msgs/Imu` | accélérations, vitesse angulaire (brutes) |
| `/mavros/rangefinder/rangefinder` | `sensor_msgs/Range` | télémètre (hauteur ou obstacle) |

### Commander le drone (publier)

| Topic | Type | Ce que c'est |
|---|---|---|
| `/mavros/setpoint_velocity/cmd_vel` | `geometry_msgs/TwistStamped` | **consigne de vitesse** (mode OFFBOARD) |
| `/mavros/setpoint_position/local` | `geometry_msgs/PoseStamped` | **consigne de position** (mode OFFBOARD) |
| `/mavros/setpoint_attitude/attitude` | `geometry_msgs/PoseStamped` | **consigne d'attitude** (mode OFFBOARD) |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | commandes RC manuelles (mode normal) |

### Appeler des actions (services)

| Service | Type | Ce que ça fait |
|---|---|---|
| `/mavros/set_mode` | `mavros_msgs/srv/SetMode` | changer de mode (`OFFBOARD`, `STABILIZE`, ...) |
| `/mavros/cmd/arming` | `mavros_msgs/srv/CommandBool` | armer / désarmer |
| `/mavros/cmd/takeoff` | `mavros_msgs/srv/CommandTOL` | décollage automatique |
| `/mavros/param/get` | `mavros_msgs/srv/ParamGet` | lire un paramètre (ex. un gain PID) |
| `/mavros/param/set` | `mavros_msgs/srv/ParamSet` | régler un paramètre |

> Astuce : pour explorer ce qui existe, dans le conteneur :
> `docker compose exec ros bash -lc "ros2 topic list"` et `... "ros2 service list"`.

---

## 3. Anatomie d'un nœud ROS2 — le squelette

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

class MonNoeud(Node):
    def __init__(self):
        super().__init__('mon_noeud')                      # nom du nœud
        self.declare_parameter('vitesse', 2.0)             # paramètre réglable
        self.pub = self.create_publisher(TwistStamped,     # ce que je publie
                                         '/mavros/setpoint_velocity/cmd_vel', 10)
        self.create_timer(0.1, self.agir)                  # boucle à 10 Hz

    def agir(self):
        sp = TwistStamped()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.twist.linear.x = self.get_parameter('vitesse').value
        self.pub.publish(sp)

def main(args=None):
    rclpy.init(args=args)
    n = MonNoeud()
    try:
        rclpy.spin(n)          # tourne indéfiniment
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

Pour recevoir une donnée, on ajoute :

```python
self.create_subscription(sensor_msgs.msg.Range, '/range/forward', self._on_range, 10)

def _on_range(self, msg):
    self.distance = msg.range     # la distance mesurée (m)
```

---

## 4. Ajouter ton package et le faire tourner

Chaque fonctionnalité est un **package** dans `ros/src/`. Un package Python contient
4 fichiers de structure + ton code :

```
ros/src/mon_package/
├── package.xml            # description du package + dépendances
├── setup.py               # déclare l'exécutable
├── setup.cfg              # (ne pas toucher)
├── resource/mon_package   # fichier vide (marqueur)
└── mon_package/
    ├── __init__.py        # fichier vide
    └── mon_package_node.py  # TON code
```

**Méthode rapide pour copier un package existant** : prends `obstacle_avoid` comme
modèle, copie le dossier, renomme partout `obstacle_avoid` en `ton_nom`.

**Lancer ton nœud** (depuis la racine du projet) :

```bash
docker compose restart ros            # reconstruit (rapide) et relance la stack
docker compose exec ros bash -lc "ros2 run ton_package ton_noeud_node"
```

> Le `restart` refait `colcon build` grâce au montage du volume, donc ton code est
> pris en compte. Tu peux aussi lancer plusieurs nœuds à la fois.

---

## 5. Le pattern OFFBOARD — décoller et voler en autonome

Pour qu'un script pilote le drone, il faut le mettre en **OFFBOARD** et **armer**.
Séquence type (dans un terminal, pendant que la simulation tourne) :

```bash
# 1) être sûr que le drone est au sol, désarmé, en STABILIZE
# 2) lancer ton script (il commence à publier des consignes)
docker compose exec ros bash -lc "ros2 run obstacle_avoid obstacle_avoid_node"

# 3) armer puis passer en OFFBOARD (via les services du nœud exemple)
docker compose exec ros bash -lc "ros2 service call /obstacle_avoid/arm std_srvs/srv/SetBool '{data: true}'"
docker compose exec ros bash -lc "ros2 service call /obstacle_avoid/offboard std_srvs/srv/SetBool '{data: true}'"
```

Règles d'or d'ArduPilot en OFFBOARD :
- **Le drone doit déjà publier des consignes** avant de passer en OFFBOARD (sinon il
  n'a « rien à suivre » et peut se comporter bizarrement).
- Le mode **OFFBOARD** dure 3 s sans consigne : il revient alors en mode précédent.
  Publie en continu (ta boucle `create_timer` le fait).
- **La RC garde toujours la priorité** : repasser en `STABILIZE` reprend la main.

> Pour les débutants : commence par décoller en **manuel** (STABILIZE/AltHold avec la
> RC), stabilise à 1-2 m, puis active ton script et enfin OFFBOARD.

---

## 6. Exemple complet : l'évitement d'obstacles

Le package **`obstacle_avoid`** est déjà dans `ros/src/`. C'est ton point de départ.

**Le pattern en 3 temps** (c'est TOUT ce qu'est l'autonomie) :

```
SENTIR                 DÉCIDER                  COMMANDER
/range/forward  →   si distance < 3 m   →   /mavros/setpoint_velocity/cmd_vel
(distance)           alors reculer            (vitesse à atteindre)
                     sinon avancer
```

### 6.1 Tester sans capteur réel (simuler l'obstacle)

Ton nœud écoute `/range/forward`. Tu peux **fabriquer cette donnée** toi-même depuis
un terminal pour tester le comportement sans capteur ni monde Gazebo :

```bash
# envoie un obstacle à 1 m (le drone doit reculer)
docker compose exec ros bash -lc \
  "ros2 topic pub -r 10 /range/forward sensor_msgs/msg/Range '{range: 1.0, min_range: 0.1, max_range: 10.0}'"

# puis éloigne l'obstacle à 20 m (le drone doit repartir en avant)
docker compose exec ros bash -lc \
  "ros2 topic pub -r 10 /range/forward sensor_msgs/msg/Range '{range: 20.0, min_range: 0.1, max_range: 10.0}'"
```

**Observe** : dans les logs du nœud, tu vois `Obstacle à 1.00 m -> recul` puis
`avancer`. C'est l'évitement qui fonctionne, sur données simulées.

### 6.2 Passer à un vrai capteur (Gazebo)

Pour que la distance vienne d'un capteur simulé dans Gazebo, il faut **ajouter un
capteur au modèle** (ex. un télémètre orienté vers l'avant) dans le monde Gazebo, et
faire remonter sa mesure. C'est une étape avancée — voir le guide simulateurs
(`GUIDE_SIMULATEURS.md`, section « Ajouter des capteurs »). Le principe reste le même :
le capteur publie sur `/range/forward` (ou un topic équivalent), ton script n'en sait
rien et continue de faire `sentir → décider → commander`.

### 6.3 Aller plus loin (les idées que tu peux implémenter)

- **Éviter latéralement** : utiliser un capteur orienté à gauche/droite et commander
  une vitesse latérale (`linear.y`) au lieu de reculer.
- **Suivre une trajectoire** : publier des consignes de position
  (`/mavros/setpoint_position/local`) qui avancent le long d'un chemin.
- **Réagir aux paramètres** : modifier un gain PID en vol depuis ton script
  (service `/mavros/param/set`), pour comparer le comportement automatiquement.
- **Gérer les modes** : basculer automatiquement en OFFBOARD/STABILIZE selon l'état.

---

## 7. Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le drone ignore les consignes | pas en OFFBOARD | vérifier `/mavros/state` : `custom_mode == OFFBOARD` |
| OFFBOARD se coupe après 3 s | plus de consigne publiée | ta boucle `create_timer` doit publier en continu |
| Service `.../set_mode` échoue | le drone ne publie pas encore | lancer le nœud AVANT d'activer OFFBOARD |
| Mon code n'est pas pris en compte | volume non relancé | `docker compose restart ros` |
| `ros2 run` ne trouve pas le package | build non fait | regarder les logs : `docker compose logs ros` |

---

## Pour aller plus loin

- Voir le fonctionnement de `joy_bridge` / `flight_control` / `pid_tuner` : ce sont
  des exemples de lecture, de commande et de réglage — lis leur code.
- Le **guide simulateurs** (`GUIDE_SIMULATEURS.md`) : comment modifier le monde Gazebo,
  ajouter des capteurs, et quels outils utiliser dans les prochains chapitres.
