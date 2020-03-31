import sys
import warnings
from functools import wraps

def ignore_warnings(f):
    @wraps(f)
    def inner(*args, **kwargs):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("ignore")
            response = f(*args, **kwargs)
        return response
    return inner

def import_qgis_processing():
    sys.path.append('/usr/lib/qgis')
    sys.path.append('/usr/share/qgis/python/plugins')
    from qgis.core import QgsApplication, QgsProcessingFeedback, QgsRasterLayer
    app = QgsApplication([], False)
    feedback = QgsProcessingFeedback()
    return (app, feedback, QgsRasterLayer)

app, feedback, QgsRasterLayer = import_qgis_processing()
app.initQgis()

@ignore_warnings # Ignored because we want the output of this script to be a single value, and "import processing" is noisy
def initialise_processing(app):
    from qgis.analysis import QgsNativeAlgorithms
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    app.processingRegistry().addProvider(QgsNativeAlgorithms())
    return (app, processing,)


def create_grid(extent):
    params = {
        'CRS': 'QgsCoordinateReferenceSystem(\'EPSG:3348\')',
        # 'EXTENT': '8254281.025715,8436867.64,1598617.582855,1680393.742855',
        'EXTENT': extent,
        'HOVERLAY': 0,
        'HSPACING': 10000,
        'TYPE': 4,
        'VOVERLAY': 0,
        'VSPACING': 10000,
        'OUTPUT': 'ogr:dbname=\'/home/kent/PycharmProjects/nrn-indicators/data/interim/pei.gpkg\' '
                  'table=\"grid\" (geom)'
    }
    return processing.run("native:creategrid", params)


app, processing = initialise_processing(app)
app.exitQgis()