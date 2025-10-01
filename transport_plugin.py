"""
Classe principale du plugin avec gestion du menu et de l'interface
"""

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
import os


class TransportExceptionnelPlugin:
    """Classe principale du plugin"""
    
    def __init__(self, iface):
        """
        Initialise le plugin
        
        :param iface: Interface QGIS
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&Transport Exceptionnel"
        
        # Enregistrer le provider Processing
        from .transport_exceptionnel_provider import TransportExceptionnelProvider
        self.provider = TransportExceptionnelProvider()
    
    def initProcessing(self):
        """Initialise le provider Processing"""
        QgsApplication.processingRegistry().addProvider(self.provider)
    
    def initGui(self):
        """Crée les entrées de menu et les boutons de barre d'outils"""
        
        # Charger l'icône
        icon_path = os.path.join(self.plugin_dir, 'wind-turbine.svg')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon()
        
        # Créer l'action pour ouvrir l'interface
        action = QAction(
            icon,
            "Analyse Transport Exceptionnel",
            self.iface.mainWindow()
        )
        action.triggered.connect(self.run)
        action.setStatusTip("Analyser la faisabilité d'un transport exceptionnel")
        
        # Ajouter au menu et à la barre d'outils
        self.iface.addPluginToMenu(self.menu, action)
        self.iface.addToolBarIcon(action)
        
        self.actions.append(action)
        
        # Initialiser Processing
        self.initProcessing()
    
    def unload(self):
        """Supprime les entrées de menu et les boutons"""
        
        # Supprimer le provider Processing
        QgsApplication.processingRegistry().removeProvider(self.provider)
        
        # Supprimer les actions du menu et de la barre d'outils
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
    
    def run(self):
        """Lance l'interface du plugin"""
        from .transport_dialog import show_transport_dialog
        show_transport_dialog()