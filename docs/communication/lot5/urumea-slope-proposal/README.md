# Urumea : proposition de reprise avec la pente et une nouvelle voix

Proposition préparée après le retour sur le montage de 64,32 s. Le film existant
reste disponible dans `../urumea-linkedin-5.1.3/`. Cette reprise n'est pas encore
tournée : les nombres ci-dessous sont des calculs préparatoires sur les mêmes
données, et non des résultats observés dans une nouvelle conversation de l'agent.

## Scénario proposé : environ 1 min 45

La pente remplace le seuil d'altitude. Le tampon rivière passe à **500 m**.
On montre chaque résultat avant de lancer l'étape suivante. La carte garde son
cadrage et occupe la même place pendant les comparaisons.

| Temps indicatif | Action visible | Texte principal à l'écran |
|---|---|---|
| 0–8 s | Carte complète, Urumea en bleu, bâtiments visibles | Saint-Sébastien · filtrer avec le relief et la rivière |
| 8–23 s | Modèle de surface puis calcul de pente ; légende lisible | Du relief à la pente · pente en % |
| 23–38 s | Moyenne zonale par emprise, coloration des bâtiments | Une pente moyenne par bâtiment |
| 38–50 s | Filtre attributaire seul ; carte complète puis résultat | Pente moyenne < 10 % |
| 50–65 s | Tampon rivière 500 m visible, puis intersection avec les bâtiments | À moins de 500 m de l'Urumea |
| 65–77 s | Routes et objets ponts filtrés autour des bâtiments retenus | Routes et ponts · rayon de 300 m |
| 77–95 s | Sauvegarde, remise à zéro, pause, rejeu seul, nouvelle pause | Enregistrer · réinitialiser · rejouer |
| 95–105 s | Export réel puis carte finale | Retrouver et exporter son analyse |

Les durées sont un objectif de montage, à ajuster à la voix retenue. Garder
4 à 6 secondes de carte stable après les résultats importants ; ne pas accélérer
les changements de carte sous une longue phrase. Si une attente est coupée,
signaler la coupe. Les sous-titres reprennent la voix en deux lignes au maximum.
Les nouveaux textes sont dans [narration.fr.json](narration.fr.json).

## Choix mesurés pour le tampon

Sur 3 073 bâtiments du jeu utilisé pour la prise 5.1.3, 1 463 ont une pente
moyenne inférieure à 10 %. En ajoutant la distance à la rivière :

| Tampon rivière | Bâtiments avec pente moyenne < 10 % |
|---|---:|
| 200 m | 410 |
| 300 m | 693 |
| **500 m** | **1 080** |
| 750 m | 1 202 |

Le choix de 500 m retient davantage de bâtiments pour la démonstration.
Les 410 et 1 080 utilisent le même critère de pente. Ne pas attribuer la
différence avec les 63 bâtiments de l'ancien film au seul tampon : l'ancien
film utilisait un seuil d'altitude différent.

Calcul préparatoire : pente de Horn GDAL en **pourcentage**, bords calculés,
sur le modèle Copernicus de 30 m en EPSG:32630 ; moyenne zonale QGIS par emprise,
puis distance géométrique métrique à l'union des deux objets rivière. Les
3 073 moyennes sont renseignées. Voir [slope-buffer-comparison.json](slope-buffer-comparison.json)
et le script `evaluate_slope.py` conservé à côté. Ce script s'exécute dans
l'image QGIS `fm-video`, avec le dossier de préparation monté sous `/review`
et le travail du film précédent sous `/source`.

Le modèle représente la surface, avec végétation et constructions, à une
résolution de 30 m. Ce n'est ni la pente d'une toiture ni une mesure fine du
terrain autour de chaque bâtiment. Afficher « Modèle de surface · 30 m »
pendant le calcul et « Seuils illustratifs · aucune prévision de crue » à la fin.

## Voix : autre générateur qu'Edge

Mon premier candidat pour la narration finale est **ElevenLabs**, avec une voix
française de narration telle que **Nicolas** ou **Guillaume**. Leur présence est
vérifiée sur la [page officielle française](https://elevenlabs.io/text-to-speech/french).
Direction proposée : ton posé, conversationnel, sobre ; phrases courtes et
pauses entre les résultats. La préférence qualitative reste à confirmer sur le
texte du film. Aucun rendu ElevenLabs personnalisé n'a été produit ici : aucun
accès à ce service n'est configuré pour ce travail.

Une alternative locale est **Kokoro**, voix française **ff_siwis**. Un véritable
extrait de 9,99 s est fourni en `voice/urumea-kokoro-fr-extrait.wav`, avec son
manifeste de génération. Les huit pistes du nouveau texte sont également
générées dans `voice/narration/` (58,91 s de voix). Le décodage complet des neuf
WAV PCM 24 kHz est contrôlé : [audio-validation.json](audio-validation.json).
Ce sont des essais d'écoute ; leur qualité n'est pas déclarée validée.
Le moteur et les modèles viennent du
[projet kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) et de la
[liste de voix du modèle](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).
La génération a été locale ; le texte n'a pas été envoyé à un service vocal.
Le moteur est sous licence MIT et le modèle sous Apache 2.0.

Pour reproduire l'extrait dans un environnement Python séparé, installer
`kokoro-onnx==0.6.1` et `soundfile`, puis récupérer les fichiers officiels
`kokoro-v1.0.onnx` et `voices-v1.0.bin` depuis la version `model-files-v1.1`
du dépôt ci-dessus. Les empreintes utilisées sont dans le manifeste.

```sh
python scripts/urumea_voice_kokoro.py \
  --spec docs/communication/lot5/urumea-slope-proposal/voice-sample.fr.json \
  --model /chemin/kokoro-v1.0.onnx \
  --voices /chemin/voices-v1.0.bin \
  --output /tmp/urumea-voice
```

Le même script accepte `narration.fr.json` pour reproduire les huit pistes du
scénario. Les modèles restent hors du dépôt et du paquet du plugin.

## Contrôles avant une nouvelle prise

- Reprendre le ZIP `dist/filter_mate_v5.1.3.zip` et enregistrer son empreinte ;
  ne pas réutiliser un dossier extrait si le ZIP a changé.
- Partir d'une copie de données inscriptible et sans filtres résiduels.
- Demander explicitement une pente en **%**, pas en degrés ; contrôler le champ
  de moyenne, les unités et le nombre de valeurs renseignées.
- Filmer d'abord le filtre de pente seul, puis le tampon de 500 m. Si l'on
  compare 200 et 500 m à l'écran, annuler le filtre spatial de 200 m avant de
  passer à 500 m : un ET entre les deux conserverait le petit tampon.
- Contrôler les nombres réels et les sous-ensembles après chaque étape. Les
  chiffres préparatoires ne remplacent pas la vérification du comportement de
  l'agent et de l'algorithme effectivement utilisés.
- Relever les comptes routes et objets ponts après le nouveau filtrage ; ils
  ne sont pas encore mesurés pour ce scénario.
- Vérifier que le favori rétablit seul les mêmes filtres et les mêmes comptes,
  puis rouvrir les fichiers exportés. Ajuster la voix à ce qui est observé.
- Écouter la prononciation d'Urumea, les pauses et les nombres avant montage.

Livré ici : scénario, texte, calculs préparatoires, script vocal, extrait et
huit pistes de narration à écouter.
Restent à produire : prise réelle pente/500 m, validation de l'agent, choix
définitif de voix et nouveau montage. Aucune publication externe.
