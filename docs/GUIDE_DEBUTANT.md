# Guide débutant — comprendre tout le système

> Tu connais les drones (physique, PID, autopilote). Ce guide explique **la partie
> logicielle** : ROS2, les topics, MAVLink, les conteneurs, et surtout **les deux
> façons de piloter** — le point qui bloque tout le monde au début.
> Lis-le dans l'ordre, une section à la fois.

---

## 1. La vue d'ensemble en une image

Ton simulateur est une **usine à données** qui tourne en continu. Chaque brique
transforme une donnée et la passe à la suivante :

```
   RC-N1 (la télécommande)
        │  paquets série (0x55...)
        ▼
   dji_host.py  (sur Windows/Linux, hors Docker)
        │  JSON par UDP (réseau)
        ▼
   joy_bridge  (dans le conteneur "ros")
        │  message ROS2 "Joy" sur le topic /joy
        ▼
   flight_control  (dans "ros")
        │  commandes RC (canaux 1-5, valeurs 1000-2000)
        ▼
   MAVROS  (dans "ros")
        │  messages MAVLink (le langage des drones)
        ▼
   ArduPilot SITL  (dans le conteneur "sim")  ← le cerveau
        │  ordres moteurs
        ▼
   Gazebo  (dans "sim")                        ← le corps et les sens
        │  état simulé (position, attitude)
        ▼
   QGroundControl (sur Windows)  ← ce que tu regardes
```

**Deux mondes** :
- **le monde "réel"** → tes deux conteneurs Docker (`sim` et `ros`) qui communiquent entre eux,
- **le monde "visible"** → QGroundControl, la fenêtre où tu vois voler le drone et où tu règles le PID.

---

## 2. Les pièces, une par une, en langage simple

### 2.1 La RC-N1 — la télécommande
C'est un objet qui produit des **valeurs de position** : chaque stick renvoie 2 valeurs
(X et Y), la molette caméra 1 valeur. Quand tu ne touches rien, tout est à 0. Quand tu
pousses un stick à fond, ça va vers ±32767.

Elle envoie ces valeurs par le **port USB-C du dessous**, comme si elle parlait par un
micro : un flux continu de petits paquets de données.

### 2.2 `dji_host.py` — le traducteur
Ce script (que je t'ai écrit) écoute ce flux série, **reconnaît** la RC-N1 parmi les
ports, lit les valeurs des sticks, et les **renvoie sur le réseau** en UDP.

> Pourquoi UDP ? Parce que les conteneurs Docker sont comme des boîtes fermées. Le
> script vit sur ton Windows (la RC y est branchée), les conteneurs vivent ailleurs.
> UDP = le moyen simple de jeter des données par-dessus le mur entre les deux.

### 2.3 Le topic `/joy` — une radio avec un nom
ROS2 organise tout avec des **topics**. Un topic est comme une **station de radio** :
quelqu'un **émet** (publish), d'autres **écoutent** (subscribe), et la station a un nom
(`/joy`, `/mavros/state`, ...). N'importe qui peut écouter ce qui passe, c'est public.

Le topic `/joy` transporte un message appelé `sensor_msgs/Joy`, qui contient :
- `axes` : un tableau de nombres, un par axe (stick gauche X/Y, stick droit X/Y, molette)
- `buttons` : un tableau pour les boutons

C'est la **représentation standard** d'un contrôleur dans ROS2 (pas un périphérique,
juste un format de données).

### 2.4 `joy_bridge` — le pont UDP → ROS2
Un petit nœud ROS2 qui écoute le port UDP 7777, reçoit les sticks envoyés par
`dji_host.py`, les met dans un message `Joy`, et les **public sur `/joy`**.

### 2.5 `flight_control` — le pilote manuel automatique
Ce nœud **écoute `/joy`** et transforme les sticks en **commandes RC** pour l'autopilote.

Une commande RC est un nombre entre **1000 et 2000** (au milieu = 1500), comme un signal
de télécommande classique. Il y a un canal par fonction :
- canal 1 = roulis, canal 2 = tangage, canal 3 = gaz, canal 4 = lacet, canal 5 = mode de vol

### 2.6 ArduPilot SITL — le cerveau (le firmware réel)
ArduPilot, c'est le **vrai firmware** qui volerait sur un vrai drone. SITL (Software In
The Loop) = on le fait tourner sur ton PC, en remplaçant les capteurs/moteurs par un
modèle. **C'est le code exact qui volera sur l'appareil** (cf. chapitre 2.12 du cours).

Il reçoit les commandes RC et il « croit » voler : il stabilise, il gère les modes de
vol, il exécute des protections.

### 2.7 MAVROS — le pont entre ROS2 et ArduPilot
MAVLink est **la langue** que parle ArduPilot (chapitre 4.7 du cours). MAVROS est le
traducteur : il transforme les topics ROS2 en messages MAVLink (et inversement), et il
les échange avec ArduPilot par le port 5760.

Grâce à MAVROS, tu peux piloter ArduPilot depuis ROS2 comme si c'était un objet ROS2
normal : topics + services.

### 2.8 Gazebo — le corps et les sens
Gazebo simule la **physique** : la gravité, les hélices, l'inertie, le vent... Il
possède aussi des **capteurs simulés** (gyroscope, accéléromètre, télémètre) et fournit
les mesures à ArduPilot. C'est lui qui décide où est le drone après que les moteurs
aient tourné.

Le lien ArduPilot ↔ Gazebo se fait par le plugin `ardupilot_gazebo`, sur le port 9002,
**en localhost** (c'est pour ça qu'ils sont dans le même conteneur `sim`).

### 2.9 QGroundControl (QGC) — la fenêtre
QGC est la **station sol**. Il se connecte à ArduPilot (port UDP 14550) et affiche :
- le drone sur une carte / en 3D,
- l'attitude (une boussole, un horizon),
- les **paramètres** de l'autopilote, dont les gains PID,
- les boutons Armer / Décoller / modes de vol.

C'est ton tableau de bord et ton outil de réglage.

---

## 3. LES DEUX MODES — le point clé

C'est ça que tu cherchais. Il y a **deux façons de piloter le même drone**, et elles ne
sont pas en concurrence — ce sont deux entrées possibles vers le même autopilote.

### Mode 1 : MANUEL — la RC est le pilote (ce qu'on a construit en premier)

```
toi (humain) → RC-N1 → dji_host → UDP → /joy → flight_control → RC channels → ArduPilot
```

C'est **toi qui tiens les manches**. L'autopilote t'obéit comme s'il recevait un vrai
récepteur RC : en Stabilize il stabilise l'attitude, en AltHold il maintient l'altitude,
etc. Le RC override que `flight_control` envoie simule exactement ce qu'un émetteur
radio ferait.

→ **Quand l'utiliser** : apprendre à piloter, tests manuels, vérifier que la RC répond.

### Mode 2 : AUTONOME — le script est le pilote (OFFBOARD)

```
ton script ROS2 → consigne (vitesse/position) → MAVROS → ArduPilot en mode OFFBOARD
```

Ici, **c'est un programme qui pilote**. ArduPilot a un mode de vol appelé **OFFBOARD**
(ou GUIDED selon le contrôleur) : dans ce mode, il ignore la RC et suit **les consignes
que tu lui envoies** — une vitesse à atteindre, une position, une attitude.

C'est LA clé pour écrire tes scripts (évitement d'obstacles, missions, etc.) : ton
programme calcule où aller, l'envoie à ArduPilot, et l'autopilote s'occupe de la
physique.

→ **Quand l'utiliser** : automatisation, évitement d'obstacles, suivi de trajectoire,
tout ce qui demande à un programme de décider.

### 3.3 Pourquoi les deux dans le même système ?

Parce que c'est **le même drone** : même autopilote, même physique. Seule l'**entrée**
change. En OFFBOARD, ton script donne des consignes et l'autopilote les exécute. Si le
script plante, tu peux **repasser en manuel** (la RC) et reprendre la main — exactement
comme en vrai. C'est la sécurité et c'est ce qui fait la richesse de la formation :
les étudiants comprennent qu'un autopilote n'est qu'un régulateur qui reçoit une
consigne, qu'elle vienne d'un humain ou d'un programme.

---

## 4. Suivre une donnée, du stick au drone — exemple concret

**Scénario** : tu pousses le stick gauche vers la gauche (roulis à gauche).

| Étape | Qui | Que se passe-t-il | Valeur |
|---|---|---|---|
| 1 | RC-N1 | le stick produit un signal électrique | `lx` devient négatif |
| 2 | `dji_host.py` | lit le paquet série | `lx = -12000` |
| 3 | réseau UDP | envoie `{"lx":-12000,...}` au conteneur | JSON |
| 4 | `joy_bridge` | crée un message `Joy`, le publie sur `/joy` | `axes[0] = -0.37` |
| 5 | `flight_control` | écoute `/joy`, calcule le canal RC | `RC1 = 1500 + (-0.37×500) = 1315` |
| 6 | MAVROS | traduit en MAVLink `RC_CHANNELS_OVERRIDE` | TCP port 5760 |
| 7 | ArduPilot SITL | reçoit, applique la commande au modèle | inclinaison à gauche |
| 8 | Gazebo | calcule la physique | le drone s'incline |
| 9 | QGC | affiche l'attitude/position | tu vois l'inclinaison |

Chaque étape est **une transformation** : un nombre devient un message, un message
devient une commande, une commande devient un mouvement. Comprendre ça, c'est comprendre
tout le système.

---

## 5. Le PID dans tout ça

Le PID n'est pas un mode : c'est un **régulateur interne à ArduPilot** qui tourne en
permanence, quel que soit le mode. Son rôle : transformer la *consigne* (angle voulu,
vitesse voulue) en *commande moteurs* pour atteindre cette consigne.

Où sont les gains ? Ce sont des **paramètres ArduPilot** : `ATC_RAT_PIT_P/I/D`
(boucle intérieure, vitesse de rotation), `ATC_ANG_PIT_P` (boucle extérieure, angle),
`INS_GYRO_FILTER` (filtre du gyro). cf. chapitre 2.12.

Deux façons de les régler en direct (c'est ce que tu as vu) :
1. **QGC** → Setup → Tuning : tu déplaces des curseurs, ArduPilot applique, le drone
   réagit sous tes yeux.
2. **ROS2** → `pid_tuner` : `ros2 param set /pid_tuner ATC_RAT_PIT_D 0.0012` applique
   la même chose via MAVROS. C'est la voie « ingénieur », scriptable.

Dans les deux cas, tu agis sur **le même réglage** : les paramètres de l'autopilote.
Le « voir le comportement » = regarder le drone dans QGC/Gazebo osciller ou converger.

---

## 6. Glossaire

| Terme | Définition courte |
|---|---|
| **Nœud (node)** | un programme ROS2 qui fait une tâche (écoute, publie, calcule) |
| **Topic** | une « radio » nommée : des messages publics, émis et écoutés |
| **Message** | le contenu qui circule sur un topic (`Joy`, `PoseStamped`, ...) |
| **Publisher / Subscriber** | émetteur / auditeur d'un topic |
| **Service** | un appel « question → réponse » (ex. régler un paramètre) |
| **MAVLink** | le langage des drones (messages de position, commandes, params) |
| **MAVROS** | le pont ROS2 ↔ MAVLink |
| **SITL** | le firmware réel tournant sans matériel, branché sur un modèle |
| **OFFBOARD / GUIDED** | mode où l'autopilote suit les consignes d'un programme |
| **RC override** | simuler une commande radio par le logiciel |
| **Setpoint** | une consigne (position, vitesse, attitude) envoyée à l'autopilote |
| **Conteneur Docker** | une « boîte » isolée contenant un logiciel complet |

---

## Prochain pas

Tu as maintenant le modèle mental. La suite logique est le guide
**[Écrire ses scripts](ECRIRE_SES_SCRIPTS.md)** : comment créer ton propre nœud ROS2
et envoyer des consignes (avec l'exemple d'évitement d'obstacles), puis le
**[Guide des simulateurs](GUIDE_SIMULATEURS.md)** pour les chapitres à venir.
