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
        
        # Préparation des paramètres pour l'algorithme Processing
        params = {
            'INPUT_TRACE': trace_layer,
            'INPUT_MNH': mnh_layer,
            'BLADE_TYPE': turbine_idx,
            'HEIGHT_REQUIRED': 5.0,
            'TRANSECT_SPACING': 1.0,
            'SAMPLE_POINTS': 9,
            'OUTPUT_ENVELOPE': 'memory:envelope',
            'OUTPUT_STATIONS': 'memory:stations',
            'OUTPUT_OBSTACLES': 'memory:obstacles',
            'OUTPUT_CSV': 'TEMPORARY_OUTPUT',
            'OUTPUT_REPORT': 'TEMPORARY_OUTPUT'
        }
        
        try:
            # Lancement de l'algorithme
            result = processing.run(
                'transport_exceptionnel:transport_exceptionnel',
                params
            )
            
            # Ajout des couches résultantes au projet
            if result.get('OUTPUT_ENVELOPE'):
                envelope_layer = result['OUTPUT_ENVELOPE']
                QgsProject.instance().addMapLayer(envelope_layer)
            
            if result.get('OUTPUT_STATIONS'):
                stations_layer = result['OUTPUT_STATIONS']
                QgsProject.instance().addMapLayer(stations_layer)
            
            if result.get('OUTPUT_OBSTACLES'):
                obstacles_layer = result['OUTPUT_OBSTACLES']
                QgsProject.instance().addMapLayer(obstacles_layer)
            
            # Message de succès
            QMessageBox.information(
                self,
                "Succès",
                "Analyse terminée !\n\n"
                "Les couches résultantes ont été ajoutées au projet."
            )
            
            # Fermer le dialogue
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'analyse :\n\n{str(e)}"
            )


def show_transport_dialog():
    """Fonction pour afficher le dialogue"""
    dialog = TransportDialog()
    dialog.exec_()


# Pour tester dans la console Python QGIS :
# from transport_exceptionnel.transport_dialog import show_transport_dialog
# show_transport_dialog()