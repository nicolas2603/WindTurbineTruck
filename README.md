# Plugin QGIS - Analyse Transport Exceptionnel Éoliennes

## Description

Ce plugin QGIS analyse la faisabilité du transport exceptionnel de pales d'éoliennes en utilisant des données LIDAR (Modèle Numérique de Hauteur). Il calcule automatiquement l'enveloppe dynamique du gabarit prenant en compte le balayage latéral dans les virages.

## Fonctionnalités

- ✅ Calcul du gabarit dynamique avec balayage dans les virages
- ✅ Support de 4 types de pales : N117 (60m), N131 (65m), N149 (75m), E82 (45m)
- ✅ Détection automatique des obstacles en hauteur
- ✅ Génération d'enveloppe par buffers dynamiques
- ✅ Export des résultats en couches vectorielles
- ✅ Rapports CSV et texte détaillés

## Installation

### Méthode 1 : Installation manuelle

1. Téléchargez le plugin
2. Extrayez le dossier dans votre répertoire de plugins QGIS :
   - **Windows** : `C:\Users\[utilisateur]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux** : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Mac** : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

3. Redémarrez QGIS
4. Activez le plugin dans : **Extensions → Installer/Gérer les extensions → Installées**

### Méthode 2 : Via le gestionnaire d'extensions

*À venir - publication sur le dépôt officiel QGIS*

## Structure du plugin

```
transport_exceptionnel/
├── __init__.py                              # Point d'entrée
├── metadata.txt                             # Métadonnées
├── icon.png                                 # Icône du plugin
├── transport_exceptionnel_provider.py       # Provider
├── transport_exceptionnel_algorithm.py      # Algorithme principal
└── README.md                                # Documentation
```

## Utilisation

### 1. Accès au plugin

Dans QGIS, allez dans :
**Traitement → Boîte à outils → Transport Exceptionnel → Analyse Transport Exceptionnel Éoliennes**

### 2. Paramètres d'entrée

| Paramètre | Type | Description |
|-----------|------|-------------|
| **Tracé du convoi** | LineString | Géométrie du parcours (ligne) |
| **MNH** | Raster | Modèle Numérique de Hauteur LIDAR |
| **Type de pale** | Liste | N117, N131, N149 ou E82 |
| **Hauteur requise** | Nombre | Gabarit vertical minimal (m) |
| **Espacement** | Nombre | Distance entre profils d'analyse (m) |
| **Points échantillon** | Entier | Nombre de points par profil transversal |

### 3. Sorties générées

| Sortie | Type | Description |
|--------|------|-------------|
| **Enveloppe dynamique** | Polygone | Gabarit complet du convoi |
| **Stations d'analyse** | Points | Profils transversaux analysés |
| **Obstacles détectés** | Points | Obstacles en hauteur détectés |
| **Rapport CSV** | Fichier | Données brutes d'analyse |
| **Rapport texte** | Fichier | Synthèse détaillée |

## Exemple d'utilisation

```python
# Via la console Python QGIS
import processing

params = {
    'INPUT_TRACE': 'chemin/vers/trace.shp',
    'INPUT_MNH': 'chemin/vers/mnh.tif',
    'BLADE_TYPE': 0,  # 0=N117, 1=N131, 2=N149, 3=E82
    'HEIGHT_REQUIRED': 5.0,
    'TRANSECT_SPACING': 1.0,
    'SAMPLE_POINTS': 9,
    'OUTPUT_ENVELOPE': 'memory:envelope',
    'OUTPUT_STATIONS': 'memory:stations',
    'OUTPUT_OBSTACLES': 'memory:obstacles',
    'OUTPUT_CSV': 'chemin/vers/rapport.csv',
    'OUTPUT_REPORT': 'chemin/vers/rapport.txt'
}

result = processing.run('transport_exceptionnel:transport_exceptionnel', params)
```

## Spécifications techniques

### Caractéristiques des turbines

| Type | Longueur pale | PàF avant | PàF arrière | Empattement | Empattement arr. | Largeur |
|------|--------------|-----------|-------------|-------------|------------------|---------|
| N117 | 60.0 m | 1.6 m | 19.1 m | 3.0 m | 36.3 m | 5.0 m |
| N131 | 65.0 m | 1.6 m | 17.9 m | 3.0 m | 47.5 m | 5.0 m |
| N149 | 75.0 m | 1.6 m | 23.2 m | 3.0 m | 57.2 m | 5.0 m |
| E82  | 45.0 m | 1.6 m | 15.0 m | 3.0 m | 30.0 m | 5.0 m |

### Calcul du balayage latéral

Le balayage latéral dans les virages est calculé selon la formule :

```
balayage = L² / (2R)
```

Où :
- **L** = longueur totale depuis le pivot (pale + moitié du tracteur)
- **R** = rayon de courbure du virage

### Validation des données

- Le raster MNH doit être dans le même CRS que le tracé
- Les valeurs NoData sont automatiquement exclues
- Les valeurs aberrantes (< -100m ou > 200m) sont filtrées

## Dépendances

- QGIS >= 3.0
- Python >= 3.6
- numpy
- GDAL/OGR
- shapely (pour l'enveloppe dynamique)

### Installation des dépendances Python

```bash
# Dans l'environnement Python de QGIS
pip install numpy shapely
```

## Limitations connues

1. **Performance** : L'analyse peut être lente pour des tracés très longs (>10 km). Recommandé : augmenter l'espacement entre profils.

2. **Résolution MNH** : La précision dépend de la résolution du raster LIDAR. Recommandé : résolution < 1m.

3. **Virages serrés** : Pour des rayons < 10m, le calcul du balayage utilise une approximation conservative.

## Exemples de résultats

### Cas 1 : Passage possible
```
✓ RÉSULTAT: PASSAGE POSSIBLE
  Aucun obstacle détecté
  Hauteur max rencontrée: 3.45m
  Largeur maximale requise: 6.23m
```

### Cas 2 : Obstacles détectés
```
✗ RÉSULTAT: 12 OBSTACLES DÉTECTÉS
  Hauteur max: 7.82m
  Dépassement max: +2.82m
  Largeur maximale requise: 8.91m
```

## Interprétation des résultats

### Enveloppe dynamique (polygone)
- Visualise l'emprise totale au sol nécessaire
- Prend en compte le balayage dans les virages
- Utile pour l'analyse d'emprise foncière

### Stations d'analyse (points)
- Chaque point = un profil transversal analysé
- Attribut `clearance` : "OK" ou "OBSTACLE"
- Attribut `width_m` : largeur dynamique requise

### Obstacles (points)
- Localisations précises des conflits
- Attribut `exceed_m` : dépassement de hauteur
- Priorisation des interventions nécessaires

## Support et contact

- **Issues** : https://github.com/votre-repo/issues
- **Email** : votre.email@example.com

## Licence

Ce plugin est distribué sous licence GPL v3.

## Crédits

Développé par [Votre Nom]

Basé sur les travaux de simulation de convois exceptionnels pour le transport d'éoliennes.

## Changelog

### Version 1.0.0 (2025-01-XX)
- Version initiale
- Calcul du gabarit dynamique
- Support de 4 types de pales
- Export multi-formats

## Feuille de route

- [ ] Ajout d'un mode "simulation interactive"
- [ ] Export des graphiques de profils
- [ ] Support de pales personnalisées
- [ ] Calcul d'itinéraires alternatifs
- [ ] Intégration avec OpenStreetMap pour vérification ponts/tunnels