"""
QGIS Plugin: Analyse Transport Exceptionnel Éoliennes
Analyse la faisabilité du transport de pales avec gabarit dynamique
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFileDestination,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsFields,
    QgsPointXY,
    QgsPoint,
    QgsWkbTypes,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
    QgsGeometryUtils,
    QgsVector,
    QgsFeatureSink
)
from qgis import processing
import numpy as np
from osgeo import gdal
import math

class TransportExceptionnelAlgorithm(QgsProcessingAlgorithm):
    """Algorithme principal d'analyse du transport exceptionnel"""
    
    # Paramètres d'entrée
    INPUT_TRACE = 'INPUT_TRACE'
    INPUT_MNH = 'INPUT_MNH'
    BLADE_TYPE = 'BLADE_TYPE'
    HEIGHT_REQUIRED = 'HEIGHT_REQUIRED'
    TRANSECT_SPACING = 'TRANSECT_SPACING'
    SAMPLE_POINTS = 'SAMPLE_POINTS'
    
    # Paramètres de sortie
    OUTPUT_ENVELOPE = 'OUTPUT_ENVELOPE'
    OUTPUT_STATIONS = 'OUTPUT_STATIONS'
    OUTPUT_OBSTACLES = 'OUTPUT_OBSTACLES'
    OUTPUT_CSV = 'OUTPUT_CSV'
    OUTPUT_REPORT = 'OUTPUT_REPORT'
    
    # Configuration des turbines
    TURBINE_SPECS = {
        'N117': {'PaF_av': 1.6, 'PaF_arr': 19.1, 'Empattement': 3, 
                 'Empattement_arr': 36.3, 'Width': 5, 'blade_length': 60.0},
        'N131': {'PaF_av': 1.6, 'PaF_arr': 17.9, 'Empattement': 3, 
                 'Empattement_arr': 47.5, 'Width': 5, 'blade_length': 65.0},
        'N149': {'PaF_av': 1.6, 'PaF_arr': 23.2, 'Empattement': 3, 
                 'Empattement_arr': 57.2, 'Width': 5, 'blade_length': 75.0},
        'E82': {'PaF_av': 1.6, 'PaF_arr': 15.0, 'Empattement': 3, 
                'Empattement_arr': 30.0, 'Width': 5, 'blade_length': 45.0}
    }
    
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
    
    def createInstance(self):
        return TransportExceptionnelAlgorithm()
    
    def name(self):
        return 'transport_exceptionnel'
    
    def displayName(self):
        return self.tr('Analyse Transport Exceptionnel Éoliennes')
    
    def group(self):
        return self.tr('Transport')
    
    def groupId(self):
        return 'transport'
    
    def shortHelpString(self):
        return self.tr("""
        Analyse la faisabilité d'un transport exceptionnel de pales d'éoliennes.
        
        Paramètres:
        - Tracé: LineString du parcours du convoi
        - MNH: Modèle Numérique de Hauteur (raster)
        - Type de pale: N117, N131, N149 ou E82
        - Hauteur requise: Gabarit vertical minimal (m)
        - Espacement: Distance entre profils d'analyse (m)
        - Points échantillon: Nombre de points par profil transversal
        
        Sorties:
        - Enveloppe dynamique du gabarit (polygone)
        - Stations d'analyse (points)
        - Obstacles détectés (points)
        - Rapport CSV
        - Rapport texte
        """)
    
    def initAlgorithm(self, config=None):
        # Couche du tracé
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_TRACE,
                self.tr('Tracé du convoi'),
                [QgsProcessing.TypeVectorLine]
            )
        )
        
        # Raster MNH
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_MNH,
                self.tr('Modèle Numérique de Hauteur (MNH)')
            )
        )
        
        # Type de pale
        self.addParameter(
            QgsProcessingParameterEnum(
                self.BLADE_TYPE,
                self.tr('Type de pale'),
                options=['N117 (60m)', 'N131 (65m)', 'N149 (75m)', 'E82 (45m)'],
                defaultValue=0
            )
        )
        
        # Hauteur requise
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HEIGHT_REQUIRED,
                self.tr('Hauteur libre requise (m)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=0.0
            )
        )
        
        # Espacement des profils
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TRANSECT_SPACING,
                self.tr('Espacement entre profils (m)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
                minValue=0.1
            )
        )
        
        # Nombre de points d'échantillonnage
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SAMPLE_POINTS,
                self.tr('Points d\'échantillonnage par profil'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=9,
                minValue=3
            )
        )
        
        # Sorties
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ENVELOPE,
                self.tr('Enveloppe dynamique'),
                type=QgsProcessing.TypeVectorPolygon
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_STATIONS,
                self.tr('Stations d\'analyse'),
                type=QgsProcessing.TypeVectorPoint
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_OBSTACLES,
                self.tr('Obstacles détectés'),
                type=QgsProcessing.TypeVectorPoint,
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_CSV,
                self.tr('Rapport CSV'),
                fileFilter='CSV files (*.csv)'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT,
                self.tr('Rapport texte'),
                fileFilter='Text files (*.txt)'
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        """Traitement principal"""
        
        # Récupération des paramètres
        trace_layer = self.parameterAsVectorLayer(parameters, self.INPUT_TRACE, context)
        mnh_layer = self.parameterAsRasterLayer(parameters, self.INPUT_MNH, context)
        blade_type_idx = self.parameterAsEnum(parameters, self.BLADE_TYPE, context)
        height_required = self.parameterAsDouble(parameters, self.HEIGHT_REQUIRED, context)
        spacing = self.parameterAsDouble(parameters, self.TRANSECT_SPACING, context)
        sample_points = self.parameterAsInt(parameters, self.SAMPLE_POINTS, context)
        
        # Validation
        if trace_layer is None:
            raise QgsProcessingException(self.tr('Couche de tracé invalide'))
        
        if mnh_layer is None:
            raise QgsProcessingException(self.tr('Raster MNH invalide'))
        
        # Type de pale
        blade_types = ['N117', 'N131', 'N149', 'E82']
        blade_type = blade_types[blade_type_idx]
        specs = self.TURBINE_SPECS[blade_type]
        
        feedback.pushInfo(f"Type de pale: {blade_type} ({specs['blade_length']}m)")
        feedback.pushInfo(f"Largeur de base: {specs['Width']}m")
        
        # Extraction de la géométrie du tracé
        feature = next(trace_layer.getFeatures())
        geom = feature.geometry()
        
        if geom.type() != QgsWkbTypes.LineGeometry:
            raise QgsProcessingException(self.tr('La couche doit être de type LineString'))
        
        # Extraction des points
        if geom.isMultipart():
            points = geom.asMultiPolyline()[0]
        else:
            points = geom.asPolyline()
        
        feedback.pushInfo(f"Tracé: {len(points)} points source")
        
        # Densification du tracé
        feedback.setProgress(10)
        stations_xy, stations_dist = self.densify_line(points, spacing)
        feedback.pushInfo(f"Tracé densifié: {len(stations_xy)} stations")
        feedback.pushInfo(f"Longueur totale: {stations_dist[-1]:.1f}m")
        
        # Ouverture du raster MNH
        feedback.setProgress(20)
        ds = gdal.Open(mnh_layer.source())
        if ds is None:
            raise QgsProcessingException(self.tr('Impossible d\'ouvrir le raster MNH'))
        
        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        gt = ds.GetGeoTransform()
        
        # Analyse des profils
        feedback.setProgress(30)
        results = []
        conflicts = []
        
        total_stations = len(stations_xy)
        
        for idx, station in enumerate(stations_xy):
            if feedback.isCanceled():
                break
            
            # Calcul de la largeur dynamique
            dynamic_half_width, radius = self.get_dynamic_half_width(
                idx, stations_xy, specs['Width'], 
                specs['blade_length'] + 18.0 / 2
            )
            
            # Direction et normale
            if idx < len(stations_xy) - 1:
                direction = np.array([
                    stations_xy[idx + 1].x() - station.x(),
                    stations_xy[idx + 1].y() - station.y()
                ])
            else:
                direction = np.array([
                    station.x() - stations_xy[idx - 1].x(),
                    station.y() - stations_xy[idx - 1].y()
                ])
            
            norm = np.linalg.norm(direction)
            if norm > 0:
                direction = direction / norm
            
            normal = np.array([-direction[1], direction[0]])
            
            # Échantillonnage transversal
            samples = np.linspace(-dynamic_half_width, dynamic_half_width, sample_points)
            xs = station.x() + samples * normal[0]
            ys = station.y() + samples * normal[1]
            
            # Lecture des hauteurs
            heights = self.sample_raster(ds, band, gt, nodata, xs, ys)
            
            valid_heights = heights[~np.isnan(heights)]
            
            if len(valid_heights) > 0:
                max_h = float(np.max(valid_heights))
                mean_h = float(np.mean(valid_heights))
                clearance_ok = max_h < height_required
            else:
                max_h = np.nan
                mean_h = np.nan
                clearance_ok = True
            
            sweep = dynamic_half_width - specs['Width'] / 2
            
            results.append({
                'station': idx,
                'distance_m': stations_dist[idx],
                'x': station.x(),
                'y': station.y(),
                'max_height_m': max_h,
                'mean_height_m': mean_h,
                'clearance_ok': clearance_ok,
                'curve_radius_m': radius if radius != np.inf else -1,
                'dynamic_half_width_m': dynamic_half_width,
                'lateral_sweep_m': sweep
            })
            
            if not clearance_ok and not np.isnan(max_h):
                conflicts.append({
                    'station': idx,
                    'distance_m': stations_dist[idx],
                    'x': station.x(),
                    'y': station.y(),
                    'max_height_m': max_h,
                    'exceedance_m': max_h - height_required,
                    'dynamic_half_width_m': dynamic_half_width
                })
            
            feedback.setProgress(30 + int(50 * idx / total_stations))
        
        ds = None  # Fermeture du raster
        
        # Création des couches de sortie
        feedback.setProgress(80)
        feedback.pushInfo("Création des couches de sortie...")
        
        # Enveloppe dynamique
        envelope_fields = QgsFields()
        envelope_fields.append(QgsField('blade_type', QVariant.String))
        envelope_fields.append(QgsField('width_max_m', QVariant.Double))
        envelope_fields.append(QgsField('length_m', QVariant.Double))
        
        (envelope_sink, envelope_dest) = self.parameterAsSink(
            parameters, self.OUTPUT_ENVELOPE, context,
            envelope_fields, QgsWkbTypes.Polygon, trace_layer.crs()
        )
        
        if envelope_sink is None:
            raise QgsProcessingException(self.tr('Impossible de créer la couche enveloppe'))
        
        feedback.pushInfo("Génération de l'enveloppe dynamique...")
        envelope_geom = self.create_dynamic_envelope(stations_xy, results, specs['Width'])
        
        if envelope_geom is None or envelope_geom.isEmpty():
            feedback.pushWarning("Enveloppe vide - problème de génération")
        else:
            envelope_feat = QgsFeature(envelope_fields)
            envelope_feat.setGeometry(envelope_geom)
            envelope_feat.setAttributes([
                blade_type,
                max([r['dynamic_half_width_m'] for r in results]) * 2,
                stations_dist[-1]
            ])
            if not envelope_sink.addFeature(envelope_feat, QgsFeatureSink.FastInsert):
                feedback.pushWarning("Échec de l'ajout de l'enveloppe")
            else:
                feedback.pushInfo(f"Enveloppe créée: {envelope_feat.geometry().area():.1f} m²")
        
        # Stations
        stations_fields = QgsFields()
        stations_fields.append(QgsField('station', QVariant.Int))
        stations_fields.append(QgsField('distance_m', QVariant.Double))
        stations_fields.append(QgsField('max_height', QVariant.Double))
        stations_fields.append(QgsField('clearance', QVariant.String))
        stations_fields.append(QgsField('width_m', QVariant.Double))
        
        (stations_sink, stations_dest) = self.parameterAsSink(
            parameters, self.OUTPUT_STATIONS, context,
            stations_fields, QgsWkbTypes.Point, trace_layer.crs()
        )
        
        if stations_sink is None:
            raise QgsProcessingException(self.tr('Impossible de créer la couche stations'))
        
        feedback.pushInfo(f"Ajout de {len(results)} stations...")
        features_added = 0
        for r in results:
            feat = QgsFeature(stations_fields)
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(r['x'], r['y'])))
            feat.setAttributes([
                r['station'],
                r['distance_m'],
                r['max_height_m'],
                'OK' if r['clearance_ok'] else 'OBSTACLE',
                r['dynamic_half_width_m'] * 2
            ])
            if stations_sink.addFeature(feat, QgsFeatureSink.FastInsert):
                features_added += 1
        
        feedback.pushInfo(f"{features_added}/{len(results)} stations ajoutées")
        
        # Obstacles
        obstacles_dest = None
        if conflicts:
            obstacles_fields = QgsFields()
            obstacles_fields.append(QgsField('station', QVariant.Int))
            obstacles_fields.append(QgsField('distance_m', QVariant.Double))
            obstacles_fields.append(QgsField('height_m', QVariant.Double))
            obstacles_fields.append(QgsField('exceed_m', QVariant.Double))
            
            (obstacles_sink, obstacles_dest) = self.parameterAsSink(
                parameters, self.OUTPUT_OBSTACLES, context,
                obstacles_fields, QgsWkbTypes.Point, trace_layer.crs()
            )
            
            if obstacles_sink is not None:
                feedback.pushInfo(f"Ajout de {len(conflicts)} obstacles...")
                for c in conflicts:
                    feat = QgsFeature(obstacles_fields)
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(c['x'], c['y'])))
                    feat.setAttributes([
                        c['station'],
                        c['distance_m'],
                        c['max_height_m'],
                        c['exceedance_m']
                    ])
                    obstacles_sink.addFeature(feat, QgsFeatureSink.FastInsert)
        
        # Export CSV et rapport
        feedback.setProgress(90)
        csv_path = self.parameterAsFileOutput(parameters, self.OUTPUT_CSV, context)
        report_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT, context)
        
        self.export_csv(results, csv_path)
        self.export_report(results, conflicts, blade_type, specs, 
                          height_required, stations_dist[-1], report_path)
        
        feedback.pushInfo(f"\n{'='*60}")
        if len(conflicts) == 0:
            feedback.pushInfo("RESULTAT: PASSAGE POSSIBLE")
            feedback.pushInfo("  Aucun obstacle detecte")
        else:
            feedback.pushInfo(f"RESULTAT: {len(conflicts)} OBSTACLES DETECTES")
            feedback.pushInfo(f"  Hauteur max: {max([c['max_height_m'] for c in conflicts]):.2f}m")
        feedback.pushInfo(f"{'='*60}\n")
        
        feedback.setProgress(100)
        
        return {
            self.OUTPUT_ENVELOPE: envelope_dest,
            self.OUTPUT_STATIONS: stations_dest,
            self.OUTPUT_OBSTACLES: obstacles_dest if conflicts else None,
            self.OUTPUT_CSV: csv_path,
            self.OUTPUT_REPORT: report_path
        }
    
    def densify_line(self, points, spacing):
        """Densifie une ligne avec un espacement régulier"""
        stations = [points[0]]
        distances = [0.0]
        cumul_dist = 0.0
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            segment_length = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
            
            num_segments = int(math.ceil(segment_length / spacing))
            
            for j in range(1, num_segments + 1):
                t = j / num_segments
                x = p1.x() + t * (p2.x() - p1.x())
                y = p1.y() + t * (p2.y() - p1.y())
                cumul_dist += segment_length / num_segments
                
                stations.append(QgsPointXY(x, y))
                distances.append(cumul_dist)
        
        return stations, np.array(distances)
    
    def calculate_curve_radius(self, stations, idx, window=3):
        """Calcule le rayon de courbure local"""
        if idx == 0 or idx >= len(stations) - 1:
            return np.inf
        
        i_before = max(0, idx - window)
        i_after = min(len(stations) - 1, idx + window)
        
        v_before = np.array([
            stations[idx].x() - stations[i_before].x(),
            stations[idx].y() - stations[i_before].y()
        ])
        
        v_after = np.array([
            stations[i_after].x() - stations[idx].x(),
            stations[i_after].y() - stations[idx].y()
        ])
        
        norm_before = np.linalg.norm(v_before)
        norm_after = np.linalg.norm(v_after)
        
        if norm_before < 1e-6 or norm_after < 1e-6:
            return np.inf
        
        cos_angle = np.clip(np.dot(v_before, v_after) / (norm_before * norm_after), -1, 1)
        angle = np.arccos(cos_angle)
        
        if angle < 0.009:  # ~0.5°
            return np.inf
        
        chord_length = math.sqrt(
            (stations[i_after].x() - stations[i_before].x())**2 +
            (stations[i_after].y() - stations[i_before].y())**2
        )
        
        if angle > 0:
            return abs(chord_length / (2 * np.sin(angle / 2)))
        
        return np.inf
    
    def get_dynamic_half_width(self, idx, stations, base_width, convoy_length):
        """Calcule la largeur dynamique avec balayage dans les virages"""
        radius = self.calculate_curve_radius(stations, idx)
        
        if radius == np.inf or radius > 500:
            sweep = 0.0
        elif radius < 10:
            sweep = convoy_length * 0.5
        else:
            sweep = (convoy_length ** 2) / (2 * radius)
        
        return base_width / 2 + sweep, radius
    
    def sample_raster(self, ds, band, gt, nodata, xs, ys):
        """Échantillonne le raster aux coordonnées données"""
        values = []
        
        for x, y in zip(xs, ys):
            px = int((x - gt[0]) / gt[1])
            py = int((y - gt[3]) / gt[5])
            
            if 0 <= px < ds.RasterXSize and 0 <= py < ds.RasterYSize:
                val = band.ReadAsArray(px, py, 1, 1)[0, 0]
                if nodata is not None and val == nodata:
                    values.append(np.nan)
                elif val < -100 or val > 200:
                    values.append(np.nan)
                else:
                    values.append(val)
            else:
                values.append(np.nan)
        
        return np.array(values)
    
    def create_dynamic_envelope(self, stations, results, base_width):
        """Crée l'enveloppe dynamique par buffers"""
        try:
            from shapely.geometry import Point
            from shapely.ops import unary_union
            
            buffers = []
            step = max(1, len(stations) // 200)
            
            for i in range(0, len(stations), step):
                pt = Point(stations[i].x(), stations[i].y())
                radius = results[i]['dynamic_half_width_m']
                buffers.append(pt.buffer(radius))
            
            if not buffers:
                return None
            
            envelope = unary_union(buffers)
            
            if envelope.geom_type == 'MultiPolygon':
                envelope = max(envelope.geoms, key=lambda p: p.area)
            
            coords = list(envelope.exterior.coords)
            qgs_points = [QgsPointXY(x, y) for x, y in coords]
            
            return QgsGeometry.fromPolygonXY([qgs_points])
            
        except ImportError:
            # Si shapely n'est pas disponible, utiliser un buffer simple QGIS
            line_points = [QgsPoint(s.x(), s.y()) for s in stations]
            line_geom = QgsGeometry.fromPolyline(line_points)
            
            # Buffer avec la largeur maximale
            max_width = max([r['dynamic_half_width_m'] for r in results])
            return line_geom.buffer(max_width, 25)
            
        except Exception as e:
            # En cas d'erreur, retourner un buffer simple
            line_points = [QgsPoint(s.x(), s.y()) for s in stations]
            line_geom = QgsGeometry.fromPolyline(line_points)
            max_width = max([r['dynamic_half_width_m'] for r in results])
            return line_geom.buffer(max_width, 25)
    
    def export_csv(self, results, path):
        """Exporte les résultats en CSV"""
        import csv
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    def export_report(self, results, conflicts, blade_type, specs, 
                     height_required, total_length, path):
        """Génère le rapport texte"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RAPPORT D'ANALYSE - TRANSPORT EXCEPTIONNEL EOLIENNES\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Type de pale: {blade_type}\n")
            f.write(f"Longueur pale: {specs['blade_length']}m\n")
            f.write(f"Largeur de base: {specs['Width']}m\n")
            f.write(f"Hauteur requise: < {height_required}m\n\n")
            
            f.write(f"Longueur totale trace: {total_length:.1f}m\n")
            f.write(f"Nombre de stations: {len(results)}\n\n")
            
            max_width = max([r['dynamic_half_width_m'] * 2 for r in results])
            f.write(f"Largeur maximale requise: {max_width:.2f}m\n\n")
            
            if len(conflicts) == 0:
                f.write("RESULTAT: PASSAGE POSSIBLE\n")
                f.write("Aucun obstacle detecte.\n")
            else:
                f.write(f"RESULTAT: {len(conflicts)} OBSTACLES DETECTES\n\n")
                f.write("DETAIL DES OBSTACLES:\n")
                for i, c in enumerate(conflicts[:20], 1):
                    f.write(f"\n  Obstacle #{i}:\n")
                    f.write(f"    PK: {c['distance_m']/1000:.3f} km\n")
                    f.write(f"    Hauteur: {c['max_height_m']:.2f}m\n")
                    f.write(f"    Depassement: +{c['exceedance_m']:.2f}m\n")