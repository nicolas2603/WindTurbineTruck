"""
Interface graphique simple pour l'analyse de transport exceptionnel
Permet de sélectionner : MNH (raster), Tracé (LineString), Type de turbine
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QMessageBox
)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsMapLayerProxyModel, QgsProject, QgsWkbTypes,
    QgsVectorLayer, QgsRasterLayer
)
import processing
import tempfile
import os


class TransportDialog(QDialog):
    """Interface simple pour choisir MNH, Tracé et Type de turbine"""
    
    TURBINE_SPECS = {
        'N117': {'blade_length': 60.0, 'description': 'N117 (60m)'},
        'N131': {'blade_length': 65.0, 'description': 'N131 (65m)'},
        'N149': {'blade_length': 75.0, 'description': 'N149 (75m)'},
        'E82': {'blade_length': 45.0, 'description': 'E82 (45m)'}
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analyse Transport Exceptionnel - Éoliennes")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Titre
        title = QLabel("<h2>Analyse de Transport Exceptionnel</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Sélection du tracé (filtre LineString)
        trace_layout = QHBoxLayout()
        trace_layout.addWidget(QLabel("Tracé du convoi:"))
        self.trace_combo = QgsMapLayerComboBox()
        self.trace_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        trace_layout.addWidget(self.trace_combo)
        layout.addLayout(trace_layout)
        
        # Sélection du MNH (filtre Raster)
        mnh_layout = QHBoxLayout()
        mnh_layout.addWidget(QLabel("Raster MNH:"))
        self.mnh_combo = QgsMapLayerComboBox()
        self.mnh_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        mnh_layout.addWidget(self.mnh_combo)
        layout.addLayout(mnh_layout)
        
        # Sélection du type de turbine
        turbine_layout = QHBoxLayout()
        turbine_layout.addWidget(QLabel("Type de pale:"))
        self.turbine_combo = QComboBox()
        for key, spec in self.TURBINE_SPECS.items():
            self.turbine_combo.addItem(spec['description'], key)
        turbine_layout.addWidget(self.turbine_combo)
        layout.addLayout(turbine_layout)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Lancer l'analyse")
        self.run_button.clicked.connect(self.run_analysis)
        self.run_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def run_analysis(self):
        """Lance l'analyse avec les paramètres sélectionnés"""
        
        # Validation des entrées
        trace_layer = self.trace_combo.currentLayer()
        if not trace_layer:
            QMessageBox.warning(
                self, 
                "Erreur", 
                "Veuillez sélectionner une couche de tracé (LineString)"
            )
            return
        
        mnh_layer = self.mnh_combo.currentLayer()
        if not mnh_layer:
            QMessageBox.warning(
                self, 
                "Erreur", 
                "Veuillez sélectionner un raster MNH"
            )
            return
        
        # Validation géométrie du tracé
        if trace_layer.geometryType() != QgsWkbTypes.LineGeometry:
            QMessageBox.warning(
                self,
                "Erreur",
                "La couche de tracé doit être de type LineString"
            )
            return
        
        # Récupération du type de turbine
        turbine_key = self.turbine_combo.currentData()
        turbine_idx = list(self.TURBINE_SPECS.keys()).index(turbine_key)
        
        # Affichage confirmation
        turbine_name = self.TURBINE_SPECS[turbine_key]['description']
        blade_length = self.TURBINE_SPECS[turbine_key]['blade_length']
        
        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Lancer l'analyse avec :\n\n"
            f"• Tracé : {trace_layer.name()}\n"
            f"• MNH : {mnh_layer.name()}\n"
            f"• Pale : {turbine_name} ({blade_length}m)\n\n"
            f"Continuer ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        # Créer un dossier temporaire pour les sorties
        temp_dir = tempfile.gettempdir()
        
        # Préparation des paramètres avec fichiers shapefile
        params = {
            'INPUT_TRACE': trace_layer,
            'INPUT_MNH': mnh_layer,
            'BLADE_TYPE': turbine_idx,
            'HEIGHT_REQUIRED': 5.0,
            'TRANSECT_SPACING': 1.0,
            'SAMPLE_POINTS': 9,
            'OUTPUT_ENVELOPE': os.path.join(temp_dir, 'envelope_transport.shp'),
            'OUTPUT_STATIONS': os.path.join(temp_dir, 'stations_transport.shp'),
            'OUTPUT_OBSTACLES': os.path.join(temp_dir, 'obstacles_transport.shp'),
            'OUTPUT_CSV': os.path.join(temp_dir, 'rapport_transport.csv'),
            'OUTPUT_REPORT': os.path.join(temp_dir, 'rapport_transport.txt')
        }
        
        try:
            # Lancement de l'algorithme
            result = processing.run(
                'transport_exceptionnel:transport_exceptionnel',
                params
            )
            
            # Charger les shapefiles créés
            envelope = QgsVectorLayer(result['OUTPUT_ENVELOPE'], 'Enveloppe dynamique', 'ogr')
            stations = QgsVectorLayer(result['OUTPUT_STATIONS'], 'Stations d\'analyse', 'ogr')
            
            layers_added = 0
            msg = "Analyse terminée !\n\n"
            
            # Ajouter l'enveloppe
            if envelope.isValid() and envelope.featureCount() > 0:
                QgsProject.instance().addMapLayer(envelope)
                msg += f"✓ Enveloppe : {envelope.featureCount()} entité(s)\n"
                layers_added += 1
            else:
                msg += "⚠ Enveloppe : vide ou invalide\n"
            
            # Ajouter les stations
            if stations.isValid() and stations.featureCount() > 0:
                QgsProject.instance().addMapLayer(stations)
                msg += f"✓ Stations : {stations.featureCount()} entité(s)\n"
                layers_added += 1
            else:
                msg += "⚠ Stations : vide ou invalide\n"
            
            # Ajouter les obstacles si présents
            if result.get('OUTPUT_OBSTACLES') and os.path.exists(result['OUTPUT_OBSTACLES']):
                obstacles = QgsVectorLayer(result['OUTPUT_OBSTACLES'], 'Obstacles détectés', 'ogr')
                if obstacles.isValid() and obstacles.featureCount() > 0:
                    QgsProject.instance().addMapLayer(obstacles)
                    msg += f"✓ Obstacles : {obstacles.featureCount()} entité(s)\n"
                    layers_added += 1
                else:
                    msg += "✓ Obstacles : aucun\n"
            else:
                msg += "✓ Obstacles : aucun\n"
            
            msg += f"\n{layers_added} couche(s) ajoutée(s) au projet"
            msg += f"\n\nRapports générés dans :\n{temp_dir}"
            
            # Message de succès
            QMessageBox.information(self, "Succès", msg)
            
            # Fermer le dialogue
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'analyse :\n\n{str(e)}\n\n"
                f"Vérifiez :\n"
                f"- Le tracé couvre bien la zone du MNH\n"
                f"- Les CRS sont compatibles\n"
                f"- Le MNH contient des données valides"
            )
            import traceback
            print("Trace complète de l'erreur :")
            traceback.print_exc()


def show_transport_dialog():
    """Fonction pour afficher le dialogue"""
    dialog = TransportDialog()
    dialog.exec_()


# Pour tester dans la console Python QGIS :
# from transport_exceptionnel.transport_dialog import show_transport_dialog
# show_transport_dialog()