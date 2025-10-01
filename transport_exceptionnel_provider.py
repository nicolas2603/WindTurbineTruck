"""
Provider pour le plugin Transport Exceptionnel
"""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .transport_exceptionnel_algorithm import TransportExceptionnelAlgorithm


class TransportExceptionnelProvider(QgsProcessingProvider):
    """Provider principal du plugin"""
    
    def __init__(self):
        super().__init__()
    
    def loadAlgorithms(self):
        """Charge les algorithmes du provider"""
        self.addAlgorithm(TransportExceptionnelAlgorithm())
    
    def id(self):
        """Identifiant unique du provider"""
        return 'transport_exceptionnel'
    
    def name(self):
        """Nom lisible du provider"""
        return self.tr('Transport Exceptionnel')
    
    def icon(self):
        """Icône du provider"""
        return QIcon(os.path.join(os.path.dirname(__file__), 'wind-turbine.svg'))
    
    def longName(self):
        """Nom long du provider"""
        return self.tr('Analyse de transport exceptionnel pour éoliennes')
    