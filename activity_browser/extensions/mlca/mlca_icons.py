# -*- coding: utf-8 -*-
from pathlib import Path

from PySide2.QtGui import QIcon

PACKAGE_DIR = Path(Path(__file__).resolve().parents[1]).resolve().parents[1]
print('>>>',PACKAGE_DIR)

def create_path(folder: str, filename: str) -> str:
    """ Builds a path to the image file.
    """
    return str(PACKAGE_DIR.joinpath("activity_browser", "static", "icons", folder, filename))


class Icons(object):
    # Icons from href="https://www.flaticon.com/

    # Modular LCA
    add_db = create_path('metaprocess', 'add_database.png')
    close_db = create_path('metaprocess', 'close_database.png')
    cut = create_path('metaprocess', 'cut.png')
    duplicate = create_path('metaprocess', 'duplicate.png')
    graph_lmp = create_path('metaprocess', 'graph_linkedmetaprocess.png')
    graph_mp = create_path('metaprocess', 'graph_metaprocess.png')
    load_db = create_path('metaprocess', 'open_database.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')
    modular_system = create_path('metaprocess', 'modular_system.png')
    new = create_path('metaprocess', 'new_metaprocess.png')
    save_db = create_path('metaprocess', 'save_database.png')
    save_mp = create_path('metaprocess', 'save_metaprocess.png')


class QIcons(Icons):
    """ Using the Icons class, returns the same attributes, but as QIcon type
    """
    def __getattribute__(self, item):
        return QIcon(Icons.__getattribute__(self, item))


mlca_icons = Icons()
mlca_qicons = QIcons()
