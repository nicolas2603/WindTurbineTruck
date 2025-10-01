"""
Plugin QGIS: Analyse Transport Exceptionnel Éoliennes
Point d'entrée avec interface graphique
"""

def classFactory(iface):
    """
    Charge le plugin dans QGIS
    
    :param iface: Interface QGIS (QgsInterface)
    :type iface: QgsInterface
    """
    from .transport_plugin import TransportExceptionnelPlugin
    return TransportExceptionnelPlugin(iface)