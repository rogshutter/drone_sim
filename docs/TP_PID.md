# TP — Réglage du PID sur le simulateur

> Objectifs : faire voler le drone simulé, modifier les gains PID, **observer le
> comportement** (oscillation, convergence, dépassement) et relier chaque gain à
> son rôle — exactement comme aux chapitres **2.7** (Régulation PID) et **2.12**
> (Mise en simulation du modèle / SITL) du cours.
>
> Durée : ~1 h. Prérequis : installation terminée (voir `INSTALL.md`), RC-N1 branchée
> et `scripts\run_dji.bat` lancé.

## Avant de commencer

- Lancez la simulation : `scripts\start.bat`
- Ouvrez **QGroundControl**, lien **UDP 14550** connecté.
- Ouvrez la **vue 3D Gazebo** : `scripts\start_gui.bat` → c'est ELLE qui montre
  le comportement physique concret. QGC sert aux paramètres et aux courbes.
- Le drone simulé doit être visible, connecté, mode **Stabilize**.
- Avec la RC-N1 : stick gauche = roulis (droite/gauche) + tangage (avant/arrière),
  stick droit = gaz + lacet. (Stick gauche/droite inversés selon la configuration
  Mode 2 — ajustable.)

> **Consigne permanente** : chaque fois que tu changes un gain, **regarde le drone
> dans la vue 3D**. C'est là que tu VOIS l'oscillation, la vibration, la divergence
> — le "concret" qui accompagne la théorie du chapitre 2.6.

## Partie A — Faire voler l'appareil

1. Vérifiez le retour de la RC : dans QGC, l'image du stick doit bouger.
2. **Armez** (bouton Arm dans QGC, ou au clavier `Ctrl`+`A`).
3. **Décollez** en Stabilize : poussez le gaz au milieu, dosez pour maintenir ~1 m.
4. Déplacez l'appareil (roulis/tangage) et posez-le.
5. **Notez** : à quel point la stabilisation tient l'attitude ? L'appareil dérive-t-il ?

## Partie B — Relever les paramètres actuels

Dans QGC : **Setup → Tuning** (ou onglet Advanced). Relevez les valeurs :

| Paramètre | Valeur | Chapitre du cours qui en établit le sens |
|---|---|---|
| `ATC_ANG_PIT_P` | ____ | 2.12.6 (boucle extérieure, vivacité) |
| `ATC_RAT_PIT_P` | ____ | 2.7 (action proportionnelle) |
| `ATC_RAT_PIT_I` | ____ | 2.7 (action intégrale) |
| `ATC_RAT_PIT_D` | ____ | 2.7 (action dérivée / amortissement) |
| `INS_GYRO_FILTER` | ____ | 2.8 (filtre gyroscope) |

> Astuce : la liste complète des paramètres est dans QGC → **Parameters**,
> cherchez `ATC_`.

## Partie C — L'expérience qui convainc (reprise de 2.12.8)

En **Altitude Hold** (maintien d'altitude, plus stable), faites une petite
manœuvre de tangage (pousser l'avant 1 s, relâcher) et observez **dans la vue 3D**.

1. **Divisez `ATC_RAT_PIT_D` par 3** → dans la vue 3D, **le drone se met à osciller
   en tangage** (l'action dérivée ne freine plus). Constatez le vocabulaire du
   chapitre 2.6 : oscillation quasi entretenue, amortissement quasi nul.
   Comparez à la courbe de QGC (Flight Review) : la théorie du chapitre 2.7 est
   visible **en 3D et sur la courbe**.
2. **Remettez la valeur d'origine.**
3. **Multipliez `ATC_ANG_PIT_P` par 2** → dans la vue 3D, le drone devient **plus
   vif** et **dépasse** davantage (pulsation propre plus élevée, amortissement
   inchangé). Observez le "jeté" à l'arrêt de la manœuvre.
4. **Remettez la valeur d'origine.**

**QCM de compréhension** : pourquoi diviser le D fait-il osciller, alors que
multiplier le gain d'angle ne fait que rendre la réponse plus vive ? (Regarde les
deux cas dans la vue 3D : dans l'un le drone oscille indéfiniment, dans l'autre il
revient vite mais dépasse un peu.)

## Partie D — Réglage méthodique d'un axe (reprise de 2.7.5)

Sur **roulis** (`ATC_RAT_ROL_P/I/D`) :

1. **P seul** : montez `ATC_RAT_ROL_P` jusqu'à voir l'appareil réagir vite mais
   commencer à osciller. Notez cette valeur.
2. **Ajoutez D** : augmentez `ATC_RAT_ROL_D` jusqu'à ce que les oscillations
   s'amortissent (viser un amortissement ≈ 0,7, dépassement ≈ 5 %).
3. **Ajoutez I** : en vol, avec un léger déséquilibre simulé (décentrer une masse
   dans QGC si possible), constatez que l'erreur résiduelle disparaît.

**Symptômes à savoir nommer** :
- P trop fort, D insuffisant → oscillations
- D trop fort → nervosité, sensibilité au bruit (chapitre 2.8)
- I trop fort → oscillations lentes, emballement (*windup*)

## Partie E — Réglage via ROS2 (la voie "ingénieur")

Dans un terminal, pendant que le simulateur tourne :

```bash
# voir le paramètre actuel
docker compose exec sim bash -lc "ros2 param get /pid_tuner ATC_RAT_PIT_P"

# le modifier — le drone réagit immédiatement
docker compose exec sim bash -lc "ros2 param set /pid_tuner ATC_RAT_PIT_D 0.0012"

# observer l'attitude en direct
docker compose exec sim bash -lc "ros2 topic echo /mavros/local_position/pose"
```

Reproduisez l'étape C-1 avec la commande ROS2 : divisez `ATC_RAT_PIT_D` par 3,
observez l'oscillation, remettez la valeur.

## Partie F — Provoquer des pannes (reprise de 2.12 exo 6 et 7)

La simulation sert à **provoquer ce qu'on ne provoquerait jamais en vrai**.

1. **Panne moteur** (exo 6) : coupez un rotor dans le modèle Gazebo (voir
   `GUIDE_SIMULATEURS.md`, section capteurs/panne, ou via QGC selon la version).
   Observez dans la vue 3D la réaction du firmware réel (perte de contrôle du
   quadrirotor). Passez sur un **hexarotor** simulé et comparez : c'est la
   redondance du chapitre 2.2, vérifiée en simulation.
2. **Perte de liaison RC** (exo 7) : régler `SIM_RC_FAIL=1` (paramètre ArduPilot,
   via QGC → Parameters) simule la perte du signal radio. Observez le comportement
   de repli (failsafe), identifiez le paramètre qui le gouverne, reliez au
   chapitre 1.6. Remettez à 0.

> Ces deux manipulations demandent des commandes exactes selon la version — à
> vérifier avec l'encadrant lors de la première prise en main du simulateur.

## Rendu attendu

1. Le tableau de la partie B **complété et sourcé** (chaque paramètre → son chapitre).
2. La réponse à la question de la partie C (2-3 phrases).
3. Une phrase par symptôme de la partie D, avec le gain qui le provoque.
4. La commande ROS2 utilisée en partie E et son effet observé.

## Pour aller plus loin

- Comparer votre simulateur 1 axe du chapitre 2.7 au SITL : superposez la réponse
  du SITL (journal de vol QGC) à celle de `simuler_attitude()`.
- Rejouer les manipulations de l'exercice 5 de 2.12 : couper un moteur en vol
  (QGC → action → moteur coupé) et observer la réaction du firmware réel.
